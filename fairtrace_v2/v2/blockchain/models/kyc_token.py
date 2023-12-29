"""Custom Models for Creating Blockchain Key."""
from django.db import models

from .. import constants
from .callback_auth import CallBackToken
from .ghost import TreasuryWallet
from .request import BlockchainRequest


# Create your models here.


class KYCTokenRequest(BlockchainRequest):
    """Request Model for creating token for a product in the blockchain."""

    action = constants.ACTION_KYC_TOKEN

    def prepare_body(self):
        """Over-ridden prepare_body to format body for the corresponding
        request type."""
        related_object = getattr(self, self.object_related_name.lower())
        body = super(KYCTokenRequest, self).prepare_body()

        params = {}
        params["token_id"] = related_object.token_id
        params["distributor_id"] = related_object.account_id

        body["params"] = params
        self.body = body
        self.save()
        return body

    def handle_response(self, response):
        """Function implemented in the subclass to handle response format."""
        related_object = getattr(self, self.object_related_name.lower())
        return related_object.handle_kyc_success(response)


class AbstractKYCToken(models.Model):
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
            create_key_request = KYCTokenRequest.objects.create(
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
    def token_id(self):
        """To be implemented in the subclass to return name."""
        raise NotImplementedError()

    @property
    def account_id(self):
        """To be implemented in the subclass to return name."""
        raise NotImplementedError()

    def handle_kyc_success(self, resp_data):
        """To be implemented in the subclass to update hash when callback is
        received."""
        raise NotImplementedError()

    @property
    def initiator_wallet(self):
        """The initiator is the project itself."""
        return TreasuryWallet()
