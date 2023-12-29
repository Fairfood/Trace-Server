"""Custom Models for Creating Blockchain Key."""
from django.db import models

from .. import constants
from ..constants import HEDERA_CONSENSUS_MESSAGE_SIZE
from .callback_auth import CallBackToken
from .request import BlockchainRequest


# Create your models here.


class SubmitMessageRequest(BlockchainRequest):
    """Request Model for creating token for a product in the blockchain."""

    action = constants.ACTION_CREATE_CONSENSUS

    def prepare_body(self):
        """Over-ridden prepare_body to format body for the corresponding
        request type."""
        related_object = getattr(self, self.object_related_name.lower())
        body = super(SubmitMessageRequest, self).prepare_body()

        message = related_object.message
        if len(message) > HEDERA_CONSENSUS_MESSAGE_SIZE:
            try:
                message = related_object.short_message
            except Exception:
                message = message[:HEDERA_CONSENSUS_MESSAGE_SIZE]

        params = {}
        params["topic_id"] = related_object.topic_id
        params["message"] = message

        body["params"] = params
        self.body = body
        self.save()
        return body

    def handle_response(self, response):
        """Function implemented in the subclass to handle response format."""
        related_object = getattr(self, self.object_related_name.lower())
        return related_object.update_message_hash(response["data"])


class AbstractConsensusMessage(models.Model):
    """Abstract base class for Blockchain Key to be imported to corresponding
    model inside the project."""

    submit_message_request = models.OneToOneField(
        BlockchainRequest,
        related_name="%(app_label)s_%(class)s_msg_req",
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True

    def initialize_message(self, user=None):
        """CreateKeyRequest is created and saves in submit_message_request,
        object_related_name is set accordingly."""
        if not self.submit_message_request:
            token = CallBackToken.objects.create(creator=user)
            create_key_request = SubmitMessageRequest.objects.create(
                callback_token=token,
                creator=user,
                object_related_name=(
                    f"{self._meta.app_label}_{self.__class__.__name__}_msg_req"
                ),
            )
            self.submit_message_request = create_key_request
            self.save()
        else:
            self.submit_message_request.callback_token.refresh()
        return self.submit_message_request

    def message_pre_check(self):
        """To perform function message_pre_check."""
        if not self.submit_message_request:
            return True, "Pre-check success"
        if self.submit_message_request.is_delayed():
            self.submit_message_request.discard()
            return True, "Pre-check success"
        if (
            self.submit_message_request.status
            != constants.BC_REQUEST_STATUS_PENDING
        ):
            return True, "Pre-check success"
        return False, "Pending request already exists"

    @property
    def topic_id(self):
        """To be implemented in the subclass to return name."""
        raise NotImplementedError()

    @property
    def message(self):
        """To be implemented in the subclass to return name."""
        raise NotImplementedError()

    def update_message_hash(self, bc_hash):
        """To be implemented in the subclass to update hash when callback is
        received."""
        raise NotImplementedError()
