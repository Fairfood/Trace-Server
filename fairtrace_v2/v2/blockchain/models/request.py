"""Blockchain Request Model."""
from copy import deepcopy
from datetime import timedelta

from django.conf import settings
from django.contrib.postgres import fields
from django.core.management.utils import get_random_secret_key
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from sentry_sdk import capture_exception

from .. import constants
from .. import library
from ..certifier import APIAuth
from .callback_auth import CallBackToken


# Create your models here.


def get_request_password():
    """To perform function get_request_password."""
    return library.encrypt(
        message=get_random_secret_key()[:32],
        encryption_key=settings.SECRET_KEY,
    )


class BlockchainRequest(models.Model):
    """Base request for all type of request to the blockchain node.

    This can be inherited and customized for each type of request
    Attributes:
        body                : To temporarily store the body before sending the
                               request
        header              : To temporarily store the header before sending
                               the request
        type                : Automatically set as the subclass's name.
        object_related_name : Automatically set as the name of the foreignkey
                              that represents the connection from the target
                              model to the request model
        callback_token      : Callback token to authenticate the callback
        receipt             : Receipt token issued from the blockchain node.
        status              : Status of the request
        updated_on
        created_on
        creator
    """

    header = None
    action = 0

    type = models.CharField(
        max_length=100, default=None, null=True, blank=True
    )
    object_related_name = models.CharField(
        max_length=100, default=None, null=True, blank=True
    )
    password = models.CharField(max_length=200, default=get_request_password)

    body = fields.JSONField(default=dict, encoder=DjangoJSONEncoder)

    callback_token = models.OneToOneField(
        CallBackToken,
        related_name="request",
        default=None,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    receipt = models.CharField(
        max_length=100, default=None, null=True, blank=True
    )
    status = models.IntegerField(
        choices=constants.BC_REQUEST_STATUS_CHOICES,
        default=constants.BC_REQUEST_STATUS_PENDING,
    )

    last_api_call = models.DateTimeField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    response = fields.JSONField(default=dict, encoder=DjangoJSONEncoder)

    def __init__(self, *args, **kwargs):
        """Overridden to set the type to subclass name."""
        kwargs["type"] = self.__class__.__name__
        super(BlockchainRequest, self).__init__(*args, **kwargs)

    def __str__(self):
        """Str representation."""
        return f"{self.type} : {self.id}"

    @property
    def idencode(self):
        """To return encoded id."""
        return library.encode(self.id)

    @property
    def child_class(self):
        """To perform function child_class."""
        return getattr(self, self.type.lower())

    @property
    def related_object(self):
        """To perform function related_object."""
        return getattr(self.child_class, self.object_related_name.lower())

    @property
    def decrypted_request_password(self):
        """To perform function crypted_request_password."""
        return library.decrypt(
            code=self.password, encryption_key=settings.SECRET_KEY
        )

    def top_up_initiator_wallet(self, retry=True):
        """To top-up initiator's wallet."""
        wallet = self.related_object.initiator_wallet
        if wallet:
            wallet.topup_hbar()
            if retry:
                wallet.deferred_requests.add(self)
        return True

    @staticmethod
    def check_balance_low(response):
        """To check if initiator's balance il low."""
        if (
            "message" in response
            and "INSUFFICIENT_PAYER_BALANCE" in response["message"]
        ):
            return True, True
        if "data" in response and type(response["data"]) is dict:
            if "initiatorBal" in response["data"]:
                if (
                    response["data"]["initiatorBal"]
                    <= constants.HBAR_MINIMUM_BALANCE
                ):
                    return True, False
        return False, False

    def prepare_header(
        self,
        public=settings.TREASURY_ACCOUNT_ID,
        private=settings.TREASURY_ENCRYPED_PRIVATE,
    ):
        """The request to the blockchain node is signed using the private key
        issued from the blockchain node manager.

        The blockchain key that takes the action is also sent in the
        context. This function formats the header accordingly.
        """
        context = {
            "private": private,
            "public": public,
            "network": settings.HEDERA_NETWORK,
        }

        auth = APIAuth(
            access_key_id=settings.BLOCKCHAIN_CLIENT_ID, context=context
        )

        signed_header = auth.sign_auth_header(
            key_file=settings.BLOCKCHAIN_PRIVATE_KEY_PATH
        )
        header = {
            "Accept": "application/json",
            "Authorization": signed_header,
            "Content-Type": "application/json",
        }
        self.header = header
        return header

    def prepare_body(self):
        """The callback url is appended onto the body for every request."""
        body = {
            "callback_url": (
                f"{settings.ROOT_URL}{reverse('update-hash')}"
                f"?token={self.callback_token.key}&"
                f"salt={self.callback_token.idencode}"
            ),
            "action": self.action,
            "ean_no": f"{self.type}_{self.id}",
            "params": {},
        }
        self.body = body
        self.save()
        return body

    def send(self):
        """To send the request."""
        self.status = constants.BC_REQUEST_STATUS_PENDING
        self.save()
        transaction.on_commit(
            lambda: library.post_blockchain_request.delay(request_id=self.id)
        )
        return True

    def manage_callback(self, response):
        """Function to manage the callback.

        updates the status of the request, marks the callback token as
        used and calls the handle_response of subclass.
        """
        try:
            child_class = self.child_class
            child_class.save_response(deepcopy(response))
            bal_low, retry = self.check_balance_low(response)
            if bal_low:
                self.top_up_initiator_wallet(retry=retry)

            success = child_class.handle_response(response)

        except Exception as e:
            success = False
            capture_exception(e)

        if not success:
            self.mark_as_failed()
            return False

        self.complete_request()
        return True

    def complete_request(self):
        """To perform function complete_request."""
        self.status = constants.BC_REQUEST_STATUS_COMPLETED
        self.save()
        self.callback_token.mark_as_used()

    def mark_as_failed(self):
        """To perform function mark_as_failed."""
        self.status = constants.BC_REQUEST_STATUS_FAILED
        self.save()
        self.callback_token.invalidate()

    def discard(self):
        """To perform function iscard."""
        if self.status == constants.BC_REQUEST_STATUS_PENDING:
            self.status = constants.BC_REQUEST_STATUS_DISCARDED
            self.save()
        self.callback_token.invalidate()
        return True

    def retry(self):
        """To perform function retry."""
        self.callback_token.refresh()
        self.child_class.send()

    def handle_response(self, response):
        """This function should be implemented in all classes that inherits
        from this baseclass to handle the request response and update the
        blockchain hash to the appropriate attribute."""
        raise NotImplementedError()

    def save_response(self, response):
        """To perform function save_response."""
        cbr = CallbackResponse.objects.create(
            request=self, data=response, success=response["success"]
        )
        return cbr

    def is_delayed(self):
        """To perform function is_delayed."""
        if self.status == constants.BC_REQUEST_STATUS_PENDING:
            if self.updated_on < timezone.now() - timedelta(
                **constants.REQUEST_DELAY_TOLERENCE
            ):
                return True
        return False

    def is_pending(self):
        """To perform function is_pending."""
        return self.status == constants.BC_REQUEST_STATUS_PENDING

    def is_completed(self):
        """To perform function is_completed."""
        return self.status == constants.BC_REQUEST_STATUS_COMPLETED

    def is_discarded(self):
        """To perform function is_discarded."""
        return self.status == constants.BC_REQUEST_STATUS_DISCARDED

    def is_failed(self):
        """To perform function is_failed."""
        return self.status == constants.BC_REQUEST_STATUS_FAILED


class CallbackResponse(models.Model):
    """Model to store responses received in callback.

    Attributes:
        request     : Request object
        response    : response text
        created_on  : Created time
    """

    request = models.ForeignKey(BlockchainRequest, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    data = fields.JSONField(default=dict, encoder=DjangoJSONEncoder)

    def __str__(self):
        """To perform function __str__."""
        return f"Resposnse for {self.request.type} | {self.id}"
