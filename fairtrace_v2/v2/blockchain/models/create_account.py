"""Custom Models for Creating Blockchain Key."""
from django.db import models
from sentry_sdk import capture_message

from .. import constants
from .. import library
from .callback_auth import CallBackToken
from .ghost import TreasuryWallet
from .request import BlockchainRequest


# Create your models here.


class CreateAccountRequest(BlockchainRequest):
    """Request Model for creating Creating key in the blockchain."""

    action = constants.ACTION_CREATE_ACCOUNT

    def prepare_body(self):
        """Over-ridden prepare_body to format body for the corresponding
        request type."""
        getattr(self, self.object_related_name.lower())
        body = super(CreateAccountRequest, self).prepare_body()
        params = {
            "init_bal": constants.INITIAL_BALANCE,
            "password": self.decrypted_request_password,
        }
        body["params"] = params

        self.body = body
        self.save()
        return body

    def handle_response(self, response):
        """Function implemented in the subclass to handle response format."""
        related_object = getattr(self, self.object_related_name.lower())

        try:
            password = self.decrypted_request_password
            private = library.decrypt(
                code=response["data"]["accountPrivate"],
                encryption_key=password,
            )
            if private:
                response["data"]["accountPrivate"] = private
        except Exception:
            capture_message("Password not encrypted")

        return related_object.update_hedera_data(response["data"])

    def save_response(self, response):
        """Saves response."""
        try:
            response["data"].pop("accountPrivate", "")
        except AttributeError:
            pass
        return super(CreateAccountRequest, self).save_response(response)


class AbstractHederaAccount(models.Model):
    """Abstract base class for Blockchain Key to be imported to corresponding
    model inside the project."""

    block_chain_request = models.OneToOneField(
        BlockchainRequest,
        related_name="%(app_label)s_%(class)s",
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
    )

    deferred_requests = models.ManyToManyField(
        BlockchainRequest, blank=True, related_name="initiator_wallet"
    )

    class Meta:
        abstract = True

    def initialize(self, user=None):
        """CreateKeyRequest is created and saves in block_chain_request,
        object_related_name is set accordingly."""
        if not self.block_chain_request:
            token = CallBackToken.objects.create(creator=user)
            create_key_request = CreateAccountRequest.objects.create(
                callback_token=token,
                creator=user,
                object_related_name=(
                    f"{self._meta.app_label}_{self.__class__.__name__}"
                ),
            )
            self.block_chain_request = create_key_request
            self.save()
        else:
            self.block_chain_request.callback_token.refresh()
        return self.block_chain_request

    def pre_check(self):
        """A pre-check."""
        if not self.block_chain_request:
            return True, "Pre-check success"
        if self.block_chain_request.is_delayed():
            self.block_chain_request.discard()
            return True, "Pre-check success"
        if (
            self.block_chain_request.status
            != constants.BC_REQUEST_STATUS_PENDING
        ):
            return True, "Pre-check success"
        return False, "Pending request already exists"

    def update_hedera_data(self, bc_hash):
        """To be implemented in the subclass to update hash when callback is
        received."""
        raise NotImplementedError()

    @property
    def initiator_wallet(self):
        """The initiator is the project itself."""
        return TreasuryWallet()

    def topup_hbar(self):
        """Implement function to top-up HBAR."""
        raise NotImplementedError()
