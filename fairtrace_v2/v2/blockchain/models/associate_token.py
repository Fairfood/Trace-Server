"""Custom Models for Creating Blockchain Key."""
from django.db import models

from .. import constants
from .callback_auth import CallBackToken
from .request import BlockchainRequest


# Create your models here.


class AssociateTokenRequest(BlockchainRequest):
    """Request Model for creating token for a product in the blockchain."""

    action = constants.ACTION_ASSOCIATE_TOKEN

    def prepare_header(self, private=None, public=None):
        """When doing a transaction, the header is signed using the owner's key
        and private."""
        related_object = getattr(self, self.object_related_name.lower())
        header = super(AssociateTokenRequest, self).prepare_header(
            public=related_object.account_id,
            private=related_object.account_private,
        )
        return header

    def prepare_body(self):
        """Over-ridden prepare_body to format body for the corresponding
        request type."""
        related_object = getattr(self, self.object_related_name.lower())
        body = super(AssociateTokenRequest, self).prepare_body()

        params = {}
        params["token_ids"] = related_object.tokens_to_associate

        body["params"] = params
        self.body = body
        self.save()
        return body

    def send(self):
        """To perform function send."""
        if not self.related_object.tokens_to_associate:
            self.discard()
            return False
        return super(AssociateTokenRequest, self).send()

    def handle_response(self, response):
        """Function implemented in the subclass to handle response format."""
        related_object = getattr(self, self.object_related_name.lower())
        return related_object.handle_success(response)


class AbstractAssociatedToken(models.Model):
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

    class Meta:
        abstract = True

    def initialize(self, user=None):
        """CreateKeyRequest is created and saves in block_chain_request,
        object_related_name is set accordingly."""
        if not self.block_chain_request:
            token = CallBackToken.objects.create(creator=user)
            associate_token_request = AssociateTokenRequest.objects.create(
                callback_token=token,
                creator=user,
                object_related_name=(
                    f"{self._meta.app_label}_{self.__class__.__name__}"
                ),
            )
            self.block_chain_request = associate_token_request
            self.save()
        else:
            self.block_chain_request.callback_token.refresh()
        return self.block_chain_request

    def pre_check(self):
        """To perform function pre_check."""
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

    @property
    def account_id(self):
        """To be implemented in the subclass to return name."""
        raise NotImplementedError()

    @property
    def account_private(self):
        """To be implemented in the subclass to return name."""
        raise NotImplementedError()

    @property
    def initiator_wallet(self):
        """To return wallet of the initiator to topup in case of low
        balance."""
        raise NotImplementedError()

    def handle_success(self, resp_data):
        """To be implemented in the subclass to update hash when callback is
        received."""
        raise NotImplementedError()
