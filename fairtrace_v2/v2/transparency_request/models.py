from common.currencies import CURRENCY_CHOICES
from common.library import _get_file_path
from common.library import _list_to_sentence
from common.models import AbstractBaseModel
from django.db import models
from django.db.models import Q
from v2.activity import constants as act_constants
from v2.activity.models import Activity
from v2.claims import constants as claim_constants
from v2.claims.models import AttachedCompanyClaim
from v2.communications import constants as notif_constants
from v2.communications.models import Notification
from v2.products import constants as product_constants

from . import constants


# Create your models here.


class TransparencyRequest(AbstractBaseModel):
    """Base Model to store all transparency requests.

    Attributes:
        number(int): Transparency request number
        requester(obj): Node that creates the TransparencyRequest
        requestee(obj): Node that completes the TransparencyRequest
    """

    request_type = models.IntegerField(
        default=constants.TRANSPARENCY_REQUEST_TYPE_TRANSACTION,
        choices=constants.TRANSPARENCY_REQUEST_TYPE_CHOICES,
    )
    number = models.IntegerField(default=None, editable=False, null=True)
    requester = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="requests_sent",
    )
    requestee = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="requests_received",
    )
    status = models.IntegerField(
        choices=constants.TRANSPARENCY_REQUEST_STATUS_CHOICES,
        default=constants.TRANSPARENCY_REQUEST_STATUS_PENDING,
    )
    note = models.TextField(default="", blank=True)
    response = models.TextField(default="", blank=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        """To perform function __str__."""
        return "%s| %s to %s" % (
            self.number,
            self.requester.full_name,
            self.requestee.full_name,
        )

    def is_modifiable(self):
        """Check if modifiable."""
        if self.status == constants.TRANSPARENCY_REQUEST_STATUS_PENDING:
            return True
        return False

    def reject(self, response=""):
        """To reject."""
        if not self.status == constants.TRANSPARENCY_REQUEST_STATUS_COMPLETED:
            self.response = response
            self.status = constants.TRANSPARENCY_REQUEST_STATUS_DECLINED
            self.save()
            return True
        return False

    def remove(self):
        """To remove."""
        if not self.status == constants.TRANSPARENCY_REQUEST_STATUS_COMPLETED:
            self.deleted = True
            self.save()
            return True
        return False

    def mark_as_complete(self):
        """To mark as complete."""
        if not self.status == constants.TRANSPARENCY_REQUEST_STATUS_COMPLETED:
            self.status = constants.TRANSPARENCY_REQUEST_STATUS_COMPLETED
            self.save()
            return True
        return False


class StockRequest(TransparencyRequest):
    """Model for Stock Request.

    Inherited Attributes:
        number(int): Transparency request number
        requester(obj): Node that creates the TransparencyRequest
        requestee(obj): Node that completes the TransparencyRequest

    Attributes:
        product(obj): Product that is being ordered
        quantity(float): Quantity of product being ordered
        unit(char): Unit of the quantity
        price(float): Price paid for the order
        currency(char): Currency of price
    """

    connection = models.ForeignKey(
        "supply_chains.Connection", on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        "products.Product", null=True, on_delete=models.SET_NULL
    )
    quantity = models.DecimalField(
        default=0.0, max_digits=25, decimal_places=3
    )
    unit = models.IntegerField(
        choices=product_constants.UNIT_CHOICES,
        default=product_constants.UNIT_KG,
    )
    price = models.FloatField(default=None, null=True, blank=True)
    currency = models.CharField(
        choices=CURRENCY_CHOICES,
        default=None,
        null=True,
        blank=True,
        max_length=5,
    )

    claims = models.ManyToManyField(
        "claims.Claim",
        through="StockRequestClaim",
        related_name="transaction_requests",
    )
    transaction = models.OneToOneField(
        "transactions.ExternalTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        kwargs[
            "request_type"
        ] = constants.TRANSPARENCY_REQUEST_TYPE_TRANSACTION
        super(StockRequest, self).__init__(*args, **kwargs)

    def __str__(self):
        """To perform function __str__."""
        return "%s| %s to %s" % (
            self.number,
            self.requester.full_name,
            self.requestee.full_name,
        )

    @property
    def unit_display(self):
        """Returns display unit."""
        return self.get_unit_display()

    def save(self, *args, **kwargs):
        """To run pre-save logic."""
        super(StockRequest, self).save(*args, **kwargs)
        if not self.number:
            self.number = self.id + 1200
            self.save()

    @property
    def claim_names(self):
        """Returns claim names."""
        claims = [i.name for i in self.claims.all()]
        if not claims:
            return "None"
        return _list_to_sentence(claims)

    def log_activity(self):
        """To log activity."""
        supply_chain = self.product.supply_chain
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_CREATED_STOCK_REQUEST,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_TRANSACTION_REQUEST,
            node=self.requester,
            supply_chain=supply_chain,
        )
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_RECEIVED_STOCK_REQUEST,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_TRANSACTION_REQUEST,
            node=self.requestee,
            supply_chain=supply_chain,
        )

    def reject(self, response=""):
        """To rejecct."""
        super(StockRequest, self).reject(response)
        supply_chain = self.product.supply_chain
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_DECLINED_STOCK_REQUEST,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_TRANSACTION_REQUEST,
            node=self.requestee,
            supply_chain=supply_chain,
        )
        Activity.log(
            event=self,
            activity_type=act_constants.STOCK_REQUEST_WAS_DECLINED,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_TRANSACTION_REQUEST,
            node=self.requester,
            supply_chain=supply_chain,
        )
        for member in self.requester.subscribers:
            Notification.notify(
                event=self,
                token=None,
                user=member,
                target_node=self.requester,
                supply_chain=supply_chain,
                actor_node=self.requestee,
                notif_type=notif_constants.NOTIF_TYPE_DECLINE_STOCK_REQUEST,
            )

    def notify(self):
        """To notify."""
        for member in self.requestee.subscribers:
            Notification.notify(
                event=self,
                token=None,
                user=member,
                target_node=self.requestee,
                supply_chain=self.product.supply_chain,
                actor_node=self.requester,
                notif_type=notif_constants.NOTIF_TYPE_RECEIVE_STOCK_REQUEST,
            )
        return True


class StockRequestClaim(AbstractBaseModel):
    """Model to store claims attached to a Stock request along with the
    verifiers.

    Attributes:
        request(obj)    : Request object
        claim(obj)      : Claim that is attached
        verifier(obj)   : Assigned Verifier. Tot mandatory.
    """

    request = models.ForeignKey(
        StockRequest, null=True, on_delete=models.CASCADE
    )
    claim = models.ForeignKey(
        "claims.Claim", null=True, on_delete=models.CASCADE
    )
    verifier = models.ForeignKey(
        "supply_chains.Node", null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        """To perform function __str__."""
        return "%s - %s | %d" % (self.request, self.claim.name, self.id)


class ClaimRequest(TransparencyRequest):
    """Model to store claim request. The type of claims can be referenecd from
    the claim object.

    Attributes:
        claim(obj)  : Claim that is requested
    """

    claim = models.ForeignKey(
        "claims.Claim", null=True, on_delete=models.CASCADE
    )

    def __str__(self):
        """To perform function __str__."""
        return "%s for %s: %s" % (
            self.claim.name,
            self.requestee.full_name,
            self.id,
        )

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        if "claim" in kwargs:
            if kwargs["claim"].scope == claim_constants.CLAIM_SCOPE_GLOBAL:
                kwargs[
                    "request_type"
                ] = constants.TRANSPARENCY_REQUEST_TYPE_CLAIM
            else:
                kwargs[
                    "request_type"
                ] = constants.TRANSPARENCY_REQUEST_TYPE_INFORMATION
        super(ClaimRequest, self).__init__(*args, **kwargs)

    @property
    def claim_attached(self):
        """Returns attached claims."""
        query = Q(
            claim=self.claim,
            node=self.requestee,
            claim__scope=claim_constants.CLAIM_SCOPE_GLOBAL,
        )
        query |= Q(
            claim=self.claim,
            node=self.requestee,
            attached_by=self.requester,
            claim__scope=claim_constants.CLAIM_SCOPE_LOCAL,
        )
        return AttachedCompanyClaim.objects.filter(query).exists()

    def log_activity(self):
        """To log activity."""
        if self.claim.scope == claim_constants.CLAIM_SCOPE_LOCAL:
            activity_in = act_constants.NODE_RECEIVED_INFORMATION_REQUEST
            activity_out = act_constants.NODE_CREATED_INFORMATION_REQUEST
            object_type = act_constants.OBJECT_TYPE_INFORMATION_REQUEST
        else:
            activity_in = act_constants.NODE_RECEIVED_CLAIM_REQUEST
            activity_out = act_constants.NODE_CREATED_CLAIM_REQUEST
            object_type = act_constants.OBJECT_TYPE_CLAIM_REQUEST
        Activity.log(
            event=self,
            activity_type=activity_out,
            node=self.requester,
            object_id=self.id,
            object_type=object_type,
        )
        Activity.log(
            event=self,
            activity_type=activity_in,
            node=self.requestee,
            object_id=self.id,
            object_type=object_type,
        )

    def reject(self, response=""):
        """To reject."""
        super(ClaimRequest, self).reject(response)
        if self.claim.scope == claim_constants.CLAIM_SCOPE_LOCAL:
            activity_requester = act_constants.INFORMATION_REQUEST_WAS_DECLINED
            activity_requestee = (
                act_constants.NODE_DECLINED_INFORMATION_REQUEST
            )
            object_type = act_constants.OBJECT_TYPE_INFORMATION_REQUEST
            notif_type = notif_constants.NOTIF_TYPE_DECLINE_INFORMATION_REQUEST
        else:
            activity_requester = act_constants.CLAIM_REQUEST_WAS_DECLINED
            activity_requestee = act_constants.NODE_DECLINED_CLAIM_REQUEST
            object_type = act_constants.OBJECT_TYPE_CLAIM_REQUEST
            notif_type = notif_constants.NOTIF_TYPE_DECLINE_CLAIM_REQUEST
        Activity.log(
            event=self,
            activity_type=activity_requestee,
            node=self.requestee,
            object_id=self.id,
            object_type=object_type,
        )
        Activity.log(
            event=self,
            activity_type=activity_requester,
            node=self.requester,
            object_id=self.id,
            object_type=object_type,
        )
        for member in self.requester.subscribers:
            Notification.notify(
                event=self,
                token=None,
                user=member,
                target_node=self.requester,
                actor_node=self.requestee,
                supply_chain=None,
                notif_type=notif_type,
            )

    def notify(self):
        """to notify."""
        if self.claim.scope == claim_constants.CLAIM_SCOPE_LOCAL:
            notif_type = notif_constants.NOTIF_TYPE_RECEIVE_INFORMATION_REQUEST
        else:
            notif_type = notif_constants.NOTIF_TYPE_RECEIVE_CLAIM_REQUEST
        for member in self.requestee.subscribers:
            Notification.notify(
                event=self,
                token=None,
                user=member,
                target_node=self.requestee,
                actor_node=self.requester,
                supply_chain=None,
                notif_type=notif_type,
            )
        return True

    def mark_as_complete(self):
        """To make as complete."""
        super(ClaimRequest, self).mark_as_complete()
        self.notify_response()

    def notify_response(self):
        """To notify response."""
        if self.claim.scope == claim_constants.CLAIM_SCOPE_LOCAL:
            activity_requester = act_constants.INFORMATION_RECEIVED_RESPONSE
            activity_requestee = act_constants.NODE_RESPOND_INFORMATION_REQUEST
            object_type = act_constants.OBJECT_TYPE_INFORMATION_REQUEST
            notif_type = notif_constants.NOTIF_TYPE_INFORMATION_RESPONSE
        else:
            activity_requester = act_constants.CLAIM_RECEIVED_RESPONSE
            activity_requestee = act_constants.NODE_RESPOND_CLAIM_REQUEST
            object_type = act_constants.OBJECT_TYPE_CLAIM_REQUEST
            notif_type = notif_constants.NOTIF_TYPE_CLAIM_RESPONSE
        Activity.log(
            event=self,
            activity_type=activity_requestee,
            node=self.requestee,
            object_id=self.id,
            object_type=object_type,
        )

        Activity.log(
            event=self,
            activity_type=activity_requester,
            node=self.requester,
            object_id=self.id,
            object_type=object_type,
        )

        for member in self.requester.subscribers:
            Notification.notify(
                event=self,
                token=None,
                user=member,
                target_node=self.requester,
                actor_node=self.requestee,
                supply_chain=None,
                notif_type=notif_type,
            )
        return True


class ClaimRequestField(AbstractBaseModel):
    """Model to store files or fields required in a claim request as well as
    store the response of the files of fields.

    Attributes:
        claim_request(obj)  : Claim request to which file is attached
        field(obj)          : Field for which the response was recorded.
        response(char)      : Response for the field if it is a char response.
        file(file)          : File field if its a file response.
    """

    claim_request = models.ForeignKey(
        ClaimRequest, related_name="fields", on_delete=models.CASCADE
    )
    field = models.ForeignKey(
        "claims.CriterionField", on_delete=models.CASCADE
    )
    response = models.CharField(max_length=1000)
    file = models.FileField(
        upload_to=_get_file_path, null=True, default=None, blank=True
    )

    def __str__(self):
        """To perform function __str__."""
        return "%s : %s" % (self.field.title, self.id)

    @property
    def responded(self):
        """Check if responded."""
        if self.file or self.response:
            return True
        return False


class ConnectionRequest(TransparencyRequest):
    """Model to store requests for mapping connections.

    Attributes:
        claim(obj): Claim that is requested
    """

    supply_chain = models.ForeignKey(
        "supply_chains.SupplyChain", on_delete=models.CASCADE
    )

    def __str__(self):
        """To perform function __str__."""
        return "%s : %s" % (self.requestee.full_name, self.id)

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        kwargs["request_type"] = constants.TRANSPARENCY_REQUEST_TYPE_CONNECTION
        super(ConnectionRequest, self).__init__(*args, **kwargs)

    def log_activity(self):
        """To log activity."""
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_CREATED_CONNECTION_REQUEST,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_CONNECTION_REQUEST,
            node=self.requester,
            supply_chain=self.supply_chain,
        )
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_RECEIVED_CONNECTION_REQUEST,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_CONNECTION_REQUEST,
            node=self.requestee,
            supply_chain=self.supply_chain,
        )

    def reject(self, response=""):
        """To reject."""
        super(ConnectionRequest, self).reject(response)
        activity_requester = act_constants.CONNECTION_REQUEST_WAS_DECLINED
        activity_requestee = act_constants.NODE_DECLINED_CONNECTION_REQUEST
        object_type = act_constants.OBJECT_TYPE_CONNECTION_REQUEST
        Activity.log(
            event=self,
            activity_type=activity_requestee,
            node=self.requestee,
            object_id=self.id,
            object_type=object_type,
            supply_chain=self.supply_chain,
        )
        Activity.log(
            event=self,
            activity_type=activity_requester,
            node=self.requester,
            object_id=self.id,
            object_type=object_type,
            supply_chain=self.supply_chain,
        )
        for member in self.requester.subscribers:
            n_type = notif_constants.NOTIF_TYPE_DECLINE_CONNECTION_REQUEST
            Notification.notify(
                event=self,
                token=None,
                user=member,
                target_node=self.requester,
                actor_node=self.requestee,
                supply_chain=None,
                notif_type=n_type,
            )

    def notify(self):
        """To notify."""
        for member in self.requestee.subscribers:
            n_type = notif_constants.NOTIF_TYPE_RECEIVE_CONNECTION_REQUEST
            Notification.notify(
                event=self,
                token=None,
                user=member,
                target_node=self.requestee,
                actor_node=self.requester,
                supply_chain=None,
                notif_type=n_type,
            )
        return True
