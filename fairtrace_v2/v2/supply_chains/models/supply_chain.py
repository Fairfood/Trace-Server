"""Models related to supply chain and connections in supply chain app."""
import os

from common import library as comm_lib
from common.exceptions import BadRequest
from common.library import _encode
from common.models import AbstractBaseModel
from django.contrib.postgres import fields
from django.db import models
from django.db import transaction
from django.utils import timezone
from haversine import haversine
from sentry_sdk import capture_exception
from sentry_sdk import capture_message
from v2.accounts.constants import VTOKEN_TYPE_INVITE
from v2.accounts.models import ValidationToken
from v2.activity import constants as act_constants
from v2.activity.models import Activity
from v2.blockchain.models.associate_token import AbstractAssociatedToken
from v2.communications import constants as comm_constants
from v2.communications.models import Notification
from v2.supply_chains.constants import BLOCKCHAIN_WALLET_TYPE_HEDERA
from v2.supply_chains.constants import BULK_UPLOAD_TYPE_CHOICES
from v2.supply_chains.constants import CONNECTION_STATUS_CHOICES
from v2.supply_chains.constants import CONNECTION_STATUS_CLAIMED
from v2.supply_chains.constants import CONNECTION_STATUS_VERIFIED
from v2.supply_chains.constants import CUSTOM_TEMP_NAME
from v2.supply_chains.constants import INVITATION_TYPE_CHOICES
from v2.supply_chains.constants import INVITATION_TYPE_DIRECT
from v2.supply_chains.constants import INVITE_RELATION_CHOICES
from v2.supply_chains.constants import INVITE_RELATION_SUPPLIER
from v2.supply_chains.constants import NODE_INVITED_BY_CHOICES
from v2.supply_chains.constants import NODE_INVITED_BY_COMPANY
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.transactions import constants as txn_constants

from ..managers import NodeSupplyChainQuerySet
from .graph import ConnectionGraphModel
from .node import Node


# Create your models here.


def _get_file_path(instance, filename):
    """
    Function to get filepath for a file to be uploaded
    Args:
        instance: instance of the file object
        filename: uploaded filename

    Returns:
        path: Path of file
    """
    type = instance.__class__.__name__.lower()
    filename = os.path.splitext(filename)
    path = "%s/%s/%s:%s" % (
        type,
        instance.id,
        CUSTOM_TEMP_NAME + "_",
        str(timezone.now().strftime("%d-%m-%Y_%H:%M:%S")) + str(filename[1]),
    )
    return path


class SupplyChain(AbstractBaseModel):
    """Supply chains available in the platform.

    It can only be added by Fairfood Admins. Normal users or companies
    cannot add new supply chains.
    """

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=1000, default="", blank=True)
    image = models.ImageField(
        upload_to=_get_file_path, null=True, default=None, blank=True
    )
    active = models.BooleanField(default=True)

    class Meta:
        """Meta class for the above model."""

        ordering = ("name",)

    def __str__(self):
        """To perform function __str__."""
        return "%s - %d" % (self.name, self.id)


class NodeSupplyChain(AbstractBaseModel):
    """Table storing which nodes can access a supply chain. It can also be used
    to check the nodes present in a supply chain.

    Attributes:
        node(obj): Foreign key to Node object.
        supply_chain(obj): Foreign key to supplychain object
        blocked(bool): A node can be blocked from a specific supplychain
                (This only disables the supplychain to show up in the dropdown
                in its connection's page. The node will still be active if
                those supplychains if it has been invited by another company).
    """

    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    supply_chain = models.ForeignKey(SupplyChain, on_delete=models.CASCADE)
    primary_operation = models.ForeignKey(
        "supply_chains.Operation",
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
        related_name="primary_node_supplychain",
    )
    other_operations = models.ManyToManyField(
        "supply_chains.Operation",
        related_name="secondary_node_supplychain",
        default=None,
        blank=True,
    )

    traceable = models.BooleanField(default=False)
    complexity = models.FloatField(default=0)
    tier_count = models.IntegerField(default=0)
    chain_length = models.FloatField(default=0.0)
    actor_count = models.IntegerField(default=0)
    supplier_count = models.IntegerField(default=0)
    farmer_count = models.IntegerField(default=0)
    invited_actor_count = models.IntegerField(default=0)
    mapped_actor_count = models.IntegerField(default=0)
    active_actor_count = models.IntegerField(default=0)
    pending_invite_count = models.IntegerField(default=0)

    operation_stats = fields.JSONField(null=True, blank=True, default=dict)
    farmer_coorinates = fields.JSONField(null=True, blank=True, default=dict)
    supplier_coorinates = fields.JSONField(null=True, blank=True, default=dict)

    buyer_ids = fields.JSONField(null=True, blank=True, default=list)
    supplier_ids = fields.JSONField(null=True, blank=True, default=list)
    farmer_ids = fields.JSONField(null=True, blank=True, default=list)
    invited_by = models.IntegerField(
        choices=NODE_INVITED_BY_CHOICES, default=NODE_INVITED_BY_COMPANY
    )
    active = models.BooleanField(default=False)

    objects = NodeSupplyChainQuerySet.as_manager()

    def __str__(self):
        """To perform function __str__."""
        return "%s - %s : %d" % (
            self.node.full_name,
            self.supply_chain.name,
            self.id,
        )

    @property
    def company_count(self):
        """To perform function company_count."""
        return self.actor_count - self.farmer_count

    @staticmethod
    def _operation_count(queryset, supply_chain=None):
        """To perform function _operation_count."""
        operation_count = {"supplier": {}, "farmer": {}}
        for item in queryset:
            nodesupplychains = item.nodesupplychain_set.filter(
                supply_chain=supply_chain
            )
            for nsc in nodesupplychains:
                if not nsc.primary_operation:
                    continue
                op_id = nsc.primary_operation.id
                nt = nsc.primary_operation.node_type
                node_type = "supplier" if nt == NODE_TYPE_COMPANY else "farmer"
                if op_id not in operation_count[node_type]:
                    operation_count[node_type][op_id] = {
                        "name": nsc.primary_operation.name,
                        "count": 1,
                    }
                else:
                    operation_count[node_type][op_id]["count"] += 1
        operation_count["farmer"] = list(operation_count["farmer"].values())
        operation_count["supplier"] = list(
            operation_count["supplier"].values()
        )
        return operation_count

    def get_stats_values(self, labels=None):
        """To perform function get_stats_values."""
        from v2.supply_chains.models import Invitation

        statistics = {}
        sup_queryset, sup_tier_data = self.node.get_supplier_chain(
            supply_chain=self.supply_chain, fast_mode=True, labels=labels
        )
        buy_queryset, buy_tier_data = self.node.get_buyer_chain(
            supply_chain=self.supply_chain, fast_mode=True, labels=labels
        )

        sup_ids = sup_queryset.values_list("id", flat=True)
        buy_ids = buy_queryset.values_list("id", flat=True)
        actor_ids = list(sup_ids) + list(buy_ids)
        all_actors = Node.objects.filter(id__in=actor_ids)
        farmers = sup_queryset.filter(type=NODE_TYPE_FARM)
        suppliers = sup_queryset.filter(type=NODE_TYPE_COMPANY)
        comp_ids = [i.id for i in suppliers] + [
            i.id for i in buy_queryset.filter(type=NODE_TYPE_COMPANY)
        ]
        comp_ids = list(set(comp_ids))
        comp_ids_incl_self = comp_ids + [self.node.id]
        companies = Node.objects.filter(id__in=comp_ids)
        companies_incl_self = Node.objects.filter(id__in=comp_ids_incl_self)

        invites = Invitation.objects.filter(
            inviter__in=companies_incl_self,
            invitee__in=companies_incl_self,
            connection__supply_chain=self.supply_chain,
        )
        sent_invites = invites.filter(email_sent=True)
        signed_up_companies = (
            companies.exclude(invitations_received__in=invites)
            .distinct("id")
            .count()
        )
        invited_actors = companies.filter(
            invitations_received__in=sent_invites
        ).distinct("id")
        active_actors = (
            companies.filter(invitations_received__in=sent_invites)
            .exclude(date_joined=None)
            .distinct("id")
        )

        statistics["actor_count"] = all_actors.count()
        statistics["supplier_count"] = suppliers.count()
        statistics["farmer_count"] = farmers.count()
        statistics["company_count"] = (
            statistics["actor_count"] - statistics["farmer_count"]
        )
        statistics["invited_actor_count"] = (
            invited_actors.count() + signed_up_companies
        )
        statistics["active_actor_count"] = (
            active_actors.count() + signed_up_companies
        )
        statistics["mapped_actor_count"] = (
            companies.count() - statistics["invited_actor_count"]
        )
        statistics["pending_invite_count"] = (
            statistics["invited_actor_count"]
            - statistics["active_actor_count"]
        )

        statistics["farmer_coorinates"] = list(
            farmers.values("latitude", "longitude")
        )
        statistics["supplier_coorinates"] = list(
            suppliers.values("latitude", "longitude")
        )

        statistics["operation_stats"] = self._operation_count(
            sup_queryset, self.supply_chain
        )
        statistics["buyer_ids"] = [i.id for i in buy_queryset]
        statistics["supplier_ids"] = [i.id for i in suppliers]
        statistics["farmer_ids"] = [i.id for i in farmers]

        sup_length = abs(max([i["tier"] for i in sup_tier_data.values()]))
        buy_length = abs(min([i["tier"] for i in buy_tier_data.values()]))
        statistics["tier_count"] = sup_length + buy_length

        sup_distance = abs(
            max([i["distance"] for i in sup_tier_data.values()])
        )
        statistics["chain_length"] = round(sup_distance, 2)

        statistics["traceable"] = bool(statistics["farmer_count"])

        complexity = 0
        complexity += statistics["tier_count"] * 5
        complexity += companies.count()
        complexity += statistics["chain_length"] / 10000
        complexity += statistics["farmer_count"] / 5
        statistics["complexity"] = complexity

        return statistics

    def update_values(self):
        """To perform function update_values."""
        statistics = self.get_stats_values()
        statistics.pop("company_count")
        for key, value in statistics.items():
            setattr(self, key, value)
        self.save()
        return True

    def make_active(self):
        """To perform function make_active."""
        self.active = True
        return True


class WalletTokenAssociation(AbstractBaseModel, AbstractAssociatedToken):
    """Model to record token associations to wallets.

    Attributes:
        node_wallet(obj)        : Wallet to associate to
        supply_chain(obj)       : Supply chain that the products being
                                     associated is part of
        success(bool)           : Whether the association is successful
        association_confirmed(bool) :
                    This is required because, multiple products
                    are being associated together, and if any one of them is
                    already associated, it throws an error that the token
                    is already associated. In such situations, the other
                    products will not be associated. Then when a transaction
                    takes place, it throws an error that a product is not
                    associated, then a new wallet token association is
                    created to associate that single product.
                    For situations when only one product is being
                    associated, and it still throws the same error,
                    then it might be an error and the association
                    need not be retried again. This attribute helps
                    to identify that.
    """

    node_wallet = models.ForeignKey(
        "supply_chains.BlockchainWallet",
        on_delete=models.CASCADE,
        related_name="associations",
    )
    supply_chain = models.ForeignKey(
        "supply_chains.SupplyChain",
        on_delete=models.CASCADE,
        related_name="associations",
    )
    success = models.BooleanField(default=False)
    association_confirmed = models.BooleanField(default=False)

    @classmethod
    def create_association(cls, wallet, supply_chain, products=None):
        """To perform function create_association."""
        if wallet.wallet_type != BLOCKCHAIN_WALLET_TYPE_HEDERA:
            print("Association only required for hedera wallets")
            return None
        from v2.products.models import NodeProduct

        association = cls.objects.create(
            node_wallet=wallet, supply_chain=supply_chain
        )
        is_empty = True
        to_associate = products or supply_chain.products.all()
        for prod in to_associate:
            np, created = NodeProduct.objects.get_or_create(
                node_wallet=wallet, product=prod
            )
            if np.association and not np.associated:
                asso = np.association
                asso.success = False
                asso.save()
                asso.associate_tokens()
                continue
            if created or not np.association:
                is_empty = False
                np.association = association
                np.save()
        if is_empty:
            association.delete()
            return None
        print("Tokens not associated. Associating.")
        association.associate_tokens()
        return association

    @property
    def account_id(self):
        """To perform function account_id."""
        return self.node_wallet.account_id

    @property
    def account_private(self):
        """To perform function account_private."""
        return self.node_wallet.decrypted_private

    @property
    def initiator_wallet(self):
        """To perform function initiator_wallet."""
        return self.node_wallet

    @property
    def tokens_to_associate(self):
        """To perform function tokens_to_associate."""
        token_ids = list(
            set([np.product.token_id for np in self.associated_products.all()])
        )
        return token_ids

    def pre_check(self):
        """To perform function pre_check."""
        success, message = super(WalletTokenAssociation, self).pre_check()
        if not success:
            return success, message
        if self.association_confirmed:
            return False, "Association is already confirmed"
        if not self.node_wallet.public:
            return False, "Wallet not set-up"
        for np in self.associated_products.all():
            if not np.product.token_id:
                np.product.create_token()
                return False, "Token not created. Creating token"
        return True, "Pre-check success"

    def associate_tokens(self):
        """To perform function associate_tokens."""
        if self.success:
            self.post_success()
            return True
        success, message = self.pre_check()
        if not success:
            print(f"{self.__class__.__name__} - {self.id} | {message}")
            return False
        try:
            request = self.initialize()
            request.send()
            return True
        except Exception as e:
            capture_exception(e)
            return False

    def validate_callback(self, response):
        """To perform function validate_callback."""
        if "message" in response:
            if "TokenAlreadyAssociatedToAccount" in response["message"]:
                return True
            capture_message(response["message"])
            print(f"Association failed with message. {response['message']}")
            return False
        return True

    def handle_success(self, response):
        """To perform function handle_success."""
        if not self.validate_callback(response):
            return False
        self.success = True
        self.save()
        for np in self.associated_products.all():
            np.associated = True
            np.save()
        if self.associated_products.count() == 1:
            self.association_confirmed = True
            self.save()
        self.post_success()
        return True

    def post_success(self):
        """To perform function post_success."""
        for np in self.associated_products.all():
            np.perform_kyc()
        return True


class Invitation(AbstractBaseModel):
    """To store invitation sent to different nodes. An invitation can be sent
    by a node directly to it's connections and also, to connections of it's
    connections (or tier 2). In both cases, the model, stores the inviter and
    the connection that was created for the invitation.

    Attributes:
        inviter (obj): Node that creates the invitation
        incharge (obj): Incharge that is assigned at the time when the Node was
                        invited.
        connection (obj): Connection that was created as part of the invitation
            It can be a tier 1 connection as well as a tier 2 connection.
        token (obj): Token that was assigned to the invitation.
        type (choices): The type of invitation. Can be,
                        - Direct
                        - Indirect
    """

    inviter = models.ForeignKey(
        Node,
        null=True,
        on_delete=models.SET_NULL,
        related_name="invitations_sent",
    )
    invitee = models.ForeignKey(
        Node,
        null=True,
        on_delete=models.SET_NULL,
        related_name="invitations_received",
    )
    connection = models.OneToOneField(
        "Connection",
        on_delete=models.CASCADE,
        related_name="invitation",
        null=True,
    )
    relation = models.IntegerField(
        choices=INVITE_RELATION_CHOICES, default=INVITE_RELATION_SUPPLIER
    )
    incharge = models.ForeignKey(
        "accounts.Person", null=True, on_delete=models.SET_NULL
    )
    message = models.TextField(default="", null=True, blank=True)

    email_sent = models.BooleanField(default=False)
    invited_on = models.DateTimeField(null=True, blank=True, default=None)
    type = models.IntegerField(
        choices=INVITATION_TYPE_CHOICES, default=INVITATION_TYPE_DIRECT
    )
    tokens = models.ManyToManyField(
        "accounts.ValidationToken", blank=True, related_name="invitations"
    )

    def __str__(self):
        """To perform function __str__."""
        return "By %s from %s to %s - %d" % (
            self.inviter.full_name,
            self.connection.buyer.full_name,
            self.connection.supplier.full_name,
            self.id,
        )

    def send_invite(self, sender=None):
        """Send Invited as member email."""

        if self.invitee.type == NODE_TYPE_FARM:
            return False

        if self.invitee.date_joined:
            notif_type = comm_constants.NOTIF_TYPE_EXISTING_NODE_INVITE
        else:
            notif_type = comm_constants.NOTIF_TYPE_NEW_NODE_INVITE

        for member in self.invitee.subscribers:
            if member.password:
                token = None
            else:
                tokens = self.tokens.filter(user=member)
                if not tokens:
                    token = ValidationToken.initialize(
                        user=member,
                        creator=self.creator,
                        type=VTOKEN_TYPE_INVITE,
                    )
                    self.tokens.add(token)
                    self.save()
                else:
                    token = tokens.first()
                    token.refresh()
            Notification.notify(
                token=token,
                event=self,
                user=member,
                supply_chain=self.connection.supply_chain,
                actor_node=self.inviter,
                target_node=self.invitee,
                notif_type=notif_type,
                sender=sender,
            )

        self.email_sent = True
        if not self.invitee.date_invited:
            invitee = self.invitee
            invitee.date_invited = timezone.now()
            invitee.save()
        self.invited_on = timezone.now()
        self.save()

        # Create a request to map connection to all newly invited companies
        self.send_initial_connection_request()

        transaction.on_commit(lambda: self.connection.update_graph_node())

    def send_initial_connection_request(self):
        """To perform function send_initial_connection_request."""
        if self.relation == INVITE_RELATION_SUPPLIER:
            from v2.transparency_request.models import ConnectionRequest

            request, created = ConnectionRequest.objects.get_or_create(
                requester=self.inviter,
                requestee=self.invitee,
                supply_chain=self.connection.supply_chain,
            )
            if created:
                request.note = (
                    "Please take some time to complete the chain by inviting"
                    " your connections."
                )
                request.save()
                request.log_activity()
                request.notify()

    def send_reminder(self, week=1):
        """Send Reminder email."""
        if not self.email_sent:
            return False
        if self.invitee.type == NODE_TYPE_FARM:
            return False

        if week == 1:
            notif_type = comm_constants.NOTIF_TYPE_WEEK_ONE_REMINDER
        elif week == 2:
            notif_type = comm_constants.NOTIF_TYPE_WEEK_TWO_REMINDER
        else:
            return False

        for member in self.invitee.subscribers:
            if member.password:
                token = None
            else:
                tokens = self.tokens.filter(user=member)
                if not tokens:
                    token = ValidationToken.initialize(
                        user=member,
                        creator=self.creator,
                        type=VTOKEN_TYPE_INVITE,
                    )
                    self.tokens.add(token)
                else:
                    token = tokens.first()
                    token.refresh()
            Notification.notify(
                token=token,
                event=self,
                user=member,
                actor_node=self.inviter,
                target_node=self.invitee,
                supply_chain=self.connection.supply_chain,
                notif_type=notif_type,
            )

    def log_activity(self):
        """To perform function log_activity."""
        supply_chain = self.connection.supply_chain
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_INVITED_NODE,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_INVITATION,
            node=self.inviter,
            supply_chain=supply_chain,
        )
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_RECEIVED_INVITATION,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_INVITATION,
            node=self.invitee,
            supply_chain=supply_chain,
        )

    @property
    def relation_text(self):
        """To perform function relation_text."""
        if self.relation == INVITE_RELATION_SUPPLIER:
            return "supply to"
        return "buy from"


class Connection(AbstractBaseModel):
    """Model to represent connection between nodes. It is assumed that, in a
    connection, the Node that is inviting is the buyer and the Node that is
    invited is the supplier. So here 'buyer' is the buyer and 'supplier' is the
    supplier. This model is used as a through model to the suppliers ManytoMany
    field in the Node, for easier querying. A connection is specific to a
    supply chain.

    Attributes:
        buyer: Node creating the connection.
        supplier: Node that the connection is added to.
        status: Status of the connection. Can be
            1: pending
            2: accepted
            3: rejected
         supply_chain(obj) : Foreign key to the SupplyChain object
         active(bool) : Represents if the supplychain is active in the
         connection. This will be True by default and can later be set to False
    """

    graph_uid = models.CharField(max_length=100, null=True, blank=True)

    buyer = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name="supplier_connections"
    )
    supplier = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name="buyer_connections"
    )
    status = models.IntegerField(
        choices=CONNECTION_STATUS_CHOICES, default=CONNECTION_STATUS_CLAIMED
    )
    supply_chain = models.ForeignKey(
        SupplyChain,
        on_delete=models.CASCADE,
        related_name="supply_chain_connections",
    )
    active = models.BooleanField(default=True)
    labels = models.ManyToManyField(
        "supply_chains.Label",
        through="supply_chains.ConnectionLabel",
        related_name="connections",
    )

    def __str__(self):
        """To perform function __str__."""
        return "%s supplies to %s in %s- %d" % (
            self.supplier.full_name,
            self.buyer.full_name,
            self.supply_chain.name,
            self.id,
        )

    def save(self, *args, **kwargs):
        """To perform function save."""
        super(Connection, self).save(*args, **kwargs)
        transaction.on_commit(lambda: self.update_graph_node())

    @property
    def graph_node(self):
        """To perform function graph_node."""
        if not self.graph_uid:
            return None
        return ConnectionGraphModel.nodes.get_or_none(uid=self.graph_uid)

    def get_or_create_graph(self):
        """To perform function get_or_create_graph."""
        dist = self.distance
        sc_id = self.supply_chain.id

        graph_node = self.graph_node
        if graph_node:
            return graph_node, False
        graph_node = ConnectionGraphModel(connection_id=self.id)
        graph_node.status = self.status
        graph_node.active = self.active
        graph_node.distance = dist
        graph_node.supply_chain_id = sc_id
        graph_node.email_sent = self.invitation.email_sent
        graph_node.labels = [
            {"id": i.id, "name": i.name} for i in self.labels.all()
        ]
        graph_node.save()
        self.graph_uid = graph_node.uid
        self.save()

        if not self.buyer.graph_node:
            self.buyer.create_or_update_graph_node()
        rel1 = graph_node.buyer.connect(self.buyer.graph_node)
        rel1.supply_chain_id = sc_id
        rel1.save()

        if not self.supplier.graph_node:
            self.supplier.create_or_update_graph_node()
        rel2 = graph_node.supplier.connect(self.supplier.graph_node)
        rel2.supply_chain_id = sc_id
        rel2.save()

        return graph_node, True

    def update_graph_node(self):
        """To perform function update_graph_node."""
        graph_node, created = self.get_or_create_graph()
        if not created:
            graph_node = self.graph_node
            graph_node.status = self.status
            graph_node.active = self.active
            graph_node.distance = self.distance
            graph_node.email_sent = self.invitation.email_sent
            graph_node.labels = [
                {"id": i.id, "name": i.name} for i in self.labels.all()
            ]
            graph_node.save()

            for tag in self.supplier_tags.all():
                tag.create_or_update_graph_relation()
            for tag in self.buyer_tags.all():
                tag.create_or_update_graph_relation()

    def disable(self):
        """To perform function isable."""
        self.active = False
        self.save()

    def verify_connection(self):
        """To perform function verify_connection."""
        if self.status == CONNECTION_STATUS_CLAIMED:
            if self.buyer.date_joined and self.supplier.date_joined:
                self.status = CONNECTION_STATUS_VERIFIED
                self.save()

    def tag_buyer(self, node, creator=None):
        """To perform function tag_buyer."""
        try:
            buyer_connection = Connection.objects.get(
                supplier=self.buyer, buyer=node, supply_chain=self.supply_chain
            )
        except Exception:
            raise BadRequest(
                "Invalid tag. corresponding connection does not exist. "
                f"{node} not connected to {self.buyer} in {self.supply_chain}"
            )

        tag, created = ConnectionTag.objects.get_or_create(
            buyer_connection=buyer_connection, supplier_connection=self
        )

        if created:
            tag.creator = creator
            tag.save()
        return tag

    def tag_buyers(self, nodes, creator=None):
        """To perform function tag_buyers."""
        for node in nodes:
            self.tag_buyer(node, creator)

    def tag_supplier(self, node, creator=None):
        """To perform function tag_supplier."""
        try:
            suppier_connection = Connection.objects.get(
                supplier=node,
                buyer=self.supplier,
                supply_chain=self.supply_chain,
            )
        except Exception:
            raise BadRequest(
                "Invalid tag. corresponding connection does not exist."
                f" {self.supplier} not connected to {node} in"
                f" {self.supply_chain}"
            )

        tag, created = ConnectionTag.objects.get_or_create(
            buyer_connection=self, supplier_connection=suppier_connection
        )

        if created:
            tag.creator = creator
            tag.save()
        return tag

    def tag_suppliers(self, nodes, creator=None):
        """To perform function tag_suppliers."""
        for node in nodes:
            self.tag_supplier(node, creator)

    @property
    def distance(self):
        """To perform function istance."""
        buyer_coord = (self.buyer.latitude, self.buyer.longitude)
        supplier_coord = (self.supplier.latitude, self.supplier.longitude)
        return haversine(buyer_coord, supplier_coord)


class ConnectionTag(AbstractBaseModel):
    """Table to represent the a buyer supplier relations. Such a relation is
    called tags.

    If A1, A2 & A3 is connected to B and B is connected to C1, C2 & C3 such
    that C1, C2 & C3 supplies to B and B supplies to A1, A2 & A3, tags can be
    added to B's connection with C1, C2 & C3. If C1 supplied to A1 via B, C2 to
    A2 and C3 to A3, then 3 tags are created for these.
    ConnectionTag1 -> Connection BC1 to Connection C1A
    ConnectionTag2 -> Connection BC2 to Connection C2A
    ConnectionTag3 -> Connection BC3 to Connection C3A

    Attributes:
        supplier_connection(obj): Foreign key to connection object
                            to identify the supplier connecion.
        buyer_connection(obj): Foreign key to connection object
                            to identify the supplier connection.
    Methods:
        is_valid
            For a tag to be valid, the corresponding connections should exist.
            the connections should be of the same supplychain
    """

    buyer_connection = models.ForeignKey(
        Connection,
        null=True,
        on_delete=models.CASCADE,
        related_name="supplier_tags",
    )
    supplier_connection = models.ForeignKey(
        Connection, on_delete=models.CASCADE, related_name="buyer_tags"
    )
    buyer_id = models.IntegerField(default=None, null=True, blank=True)
    supplier_id = models.IntegerField(default=None, null=True, blank=True)

    class Meta:
        unique_together = ["buyer_connection", "supplier_connection"]

    def __str__(self):
        """To perform function __str__."""
        return "%s to %s via %s - %s" % (
            self.supplier_connection.supplier,
            self.buyer_connection.buyer.full_name,
            self.supplier_connection.buyer,
            self.id,
        )

    def save(self, *args, **kwargs):
        """To perform function save."""
        super(ConnectionTag, self).save(*args, **kwargs)
        transaction.on_commit(lambda: self.create_or_update_graph_relation())

    def delete(self, using=None, keep_parents=False):
        """To perform function lete."""
        try:
            self.buyer_connection.graph_node.supplier_tag.disconnect(
                self.supplier_connection.graph_node
            )
        except Exception as e:
            print(e)
            pass
        return super(ConnectionTag, self).delete(using, keep_parents)

    def is_valid(self):
        """To perform function is_valid."""
        if self.buyer_connection.supplier == self.supplier_connection.buyer:
            if (
                self.buyer_connection.supply_chain
                == self.supplier_connection.supply_chain
            ):
                return True
        return False

    def create_or_update_graph_relation(self):
        """To perform function create_or_update_graph_relation."""
        if not self.buyer_connection.graph_node:
            self.buyer_connection.get_or_create_graph()
        if not self.supplier_connection.graph_node:
            self.supplier_connection.get_or_create_graph()
        tag_rel = self.buyer_connection.graph_node.supplier_tag.relationship(
            self.supplier_connection.graph_node
        )
        if not tag_rel:
            tag_rel = self.buyer_connection.graph_node.supplier_tag.connect(
                self.supplier_connection.graph_node
            )
        _s = self.supplier_connection.distance + self.buyer_connection.distance
        tag_rel.distance = _s / 2
        tag_rel.supply_chain_id = self.supplier_connection.supply_chain.id
        tag_rel.tag_id = self.id
        tag_rel.save()
        return True

    @property
    def buyer_idencode(self):
        """To perform function buyer_idencode."""
        if self.buyer_id:
            return _encode(self.buyer_id)
        else:
            buyer_id = self.buyer_connection.buyer.id
            self.buyer_id = buyer_id
            self.save()
            return _encode(buyer_id)

    @property
    def supplier_idencode(self):
        """To perform function supplier_idencode."""
        if self.supplier_id:
            return _encode(self.supplier_id)
        else:
            supplier_id = self.supplier_connection.supplier.id
            self.supplier_id = supplier_id
            self.save()
            return _encode(supplier_id)


class AdminInvitation(AbstractBaseModel):
    """To store invitation sent by admin different nodes.

    Attributes:
        invitee (obj): Node that receive the invitation
        tokens (obj): Foreign key to validation token object.
        node_supply_chain(objs):Supply chain from which the invitation
                              was created.Automatically created when
                              creating,node supply chain.
    """

    invitee = models.ForeignKey(
        Node,
        null=True,
        on_delete=models.SET_NULL,
        related_name="admin_invitations_received",
    )
    tokens = models.ManyToManyField(
        "accounts.ValidationToken",
        blank=True,
        related_name="admin_invitations",
    )
    node_supply_chains = models.ManyToManyField(
        NodeSupplyChain, blank=True, related_name="admin_invitations"
    )

    def __str__(self):
        """To perform function __str__."""
        return f"{self.id}"

    def send_invite(self, sender=None):
        """Send Invited as member email."""
        if self.invitee.date_joined:
            notif_type = comm_constants.NOTIF_TYPE_FFADMIN_EXISTING_NODE_INVITE
        else:
            notif_type = comm_constants.NOTIF_TYPE_FFADMIN_NEW_NODE_INVITE

        supply_chain = self.node_supply_chains.first().supply_chain

        for member in self.invitee.subscribers:
            if member.password:
                token = None
            else:
                tokens = self.tokens.filter(user=member)
                if not tokens:
                    token = ValidationToken.initialize(
                        user=member,
                        creator=self.creator,
                        type=VTOKEN_TYPE_INVITE,
                    )
                    self.tokens.add(token)
                else:
                    token = tokens.first()
                    token.refresh()

            Notification.notify(
                token=token,
                event=self,
                user=member,
                supply_chain=supply_chain,
                actor_node=None,
                target_node=self.invitee,
                notif_type=notif_type,
                sender=sender,
            )

        if not self.invitee.date_invited:
            invitee = self.invitee
            invitee.date_invited = timezone.now()
            invitee.save()
        self.save()

    def log_activity(self):
        """To perform function log_activity."""
        sc = self.node_supply_chains.first().supply_chain.id
        supply_chain = SupplyChain.objects.get(id=sc)
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_RECEIVED_INVITATION_FROM_FFADMIN,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_FFADMIN_INVITATION,
            node=self.invitee,
            supply_chain=supply_chain,
        )

    def log_joined_activity(self):
        """To perform function log_joined_activity."""
        sc = self.node_supply_chains.first().supply_chain.id
        supply_chain = SupplyChain.objects.get(id=sc)
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_JOINED_FFADMIN_INVITE,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_FFADMIN_INVITATION,
            node=self.invitee,
            supply_chain=supply_chain,
        )

    @property
    def email_sc_text(self):
        """To perform function mail_sc_text."""
        sc_count = self.node_supply_chains.count()
        sc_name = self.node_supply_chains.first().supply_chain.name
        if sc_count == 1:
            text = f"{sc_name} supply chain"
        elif sc_count == 2:
            sc_name_2 = self.node_supply_chains.last().supply_chain.name
            text = f"{sc_name} and {sc_name_2} supply chains"
        else:
            text = f"{sc_name} and {sc_count - 1} other supply chains"
        return text

    @property
    def set_activity_text(self):
        """To perform function set_activity_text."""
        if self.node_supply_chains.count() == 1:
            node_text = "Invited in a supply chain from FairFood admin"
        else:
            node_text = (
                "Invited in "
                + str(self.node_supply_chains.count())
                + " supply's chain from FairFood admin"
            )
        return node_text

    @property
    def set_joined_activity_text(self):
        """To perform function set_joined_activity_text."""
        if self.node_supply_chains.count() == 1:
            node_text = "joined in a supply chain from FairFood admin"
        else:
            node_text = (
                "Joined in "
                + str(self.node_supply_chains.count())
                + " supply's chain from FairFood admin"
            )
        return node_text

    @property
    def set_activity_user(self):
        """To perform function set_activity_user."""
        sc = self.node_supply_chains.first().supply_chain.name
        if self.node_supply_chains.count() == 1:
            user_text = sc + " supply chain"
        else:
            user_text = (
                str(self.node_supply_chains.count()) + " supply chain's"
            )
        return user_text


class Label(AbstractBaseModel):
    """Model to store the labels in the system.

    Attributes:
        name(str)       : Name of the label
        added_by(str)   : The node that create the label
    """

    name = models.CharField(max_length=50)
    supply_chains = models.ManyToManyField(
        SupplyChain, related_name="labels", blank=True
    )
    added_by = models.ForeignKey(
        Node,
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="labels_created",
    )

    def __str__(self):
        """To perform function __str__."""
        return self.name

    @property
    def removable(self):
        """To perform function removable."""
        return not self.connections.exists()


class ConnectionLabel(AbstractBaseModel):
    """Model to attach labels to connection to be able to filter connections by
    these labels.

    Attributes:
        connection(str) : Connection to which, the label is attached
        label(str)      : The label that is attached
    """

    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    def __str__(self):
        """To perform function __str__."""
        return (
            f"{self.label.name} on Connection '{self.connection.id}' -"
            f" {self.id}"
        )


class BulkExcelUploads(AbstractBaseModel):
    """Model to store the bulk upload files and also track the progress of
    adding connections.

    Attributes:
        node(obj)               : Node that is doing the operation
        supply_chain(obj)       : Supplychain to which the actions is done
        type(int)               : Type of file, can be,
                                    - Connection only
                                    - Transaction only
                                    - Connection and transaction
        file(file)              : File that is uploaded
        data(json)              : Data that is uploaded
        errors(json)            : Errors in the data
        farmers_to_add(int)     : Number of new farmers in the excel
        farmers_added(int)      : Farmers successfully added
        farmers_to_update(int)  : Farmers to be updated
        farmers_updated(int)    : Farmers successfully updated
        transactions_to_add(int): Transactions to be added
        transactions_added(int) : Transactions successfully added
        used(bool)              : Whether the file is used or not.
    """

    node = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name="bulk_uploads"
    )
    supply_chain = models.ForeignKey(
        SupplyChain,
        on_delete=models.CASCADE,
        related_name="bulk_uploads",
        null=True,
        blank=True,
    )

    type = models.IntegerField(choices=BULK_UPLOAD_TYPE_CHOICES)

    file = models.FileField(upload_to=_get_file_path, blank=True, null=True)
    file_hash = models.CharField(max_length=500, null=True, blank=True)
    data = fields.JSONField(null=True, blank=True, default=list)
    errors = fields.JSONField(null=True, blank=True, default=list)

    farmers_to_add = models.IntegerField(default=0)
    farmers_added = models.IntegerField(default=0)
    farmers_to_update = models.IntegerField(default=0)
    farmers_updated = models.IntegerField(default=0)
    transactions_to_add = models.IntegerField(default=0)
    transactions_added = models.IntegerField(default=0)
    used = models.BooleanField(default=False)

    def __str__(self):
        """To perform function __str__."""
        return f"Bulk operation - {self.node.full_name} | {self.id}"

    @classmethod
    def is_file_exists(cls, file, node):
        """Check file is already uploaded or not. also pass file hash value in
        response.

        file    : file that check is exists or not.
        node    : company id.
        """

        file_hash = comm_lib._hash_file(file)
        res = {"valid": False, "message": None, "file_hash": file_hash}
        try:
            bulk_upload = BulkExcelUploads.objects.get(
                file_hash=file_hash, used=True, node=node
            )
        except Exception:
            return res
        message = txn_constants.DUPLICATE_TXN_MSG % (
            str(bulk_upload.updated_on.strftime("%d %B %Y"))
        )
        res["valid"] = True
        res["message"] = message
        return res


class UploadFarmerMapping(AbstractBaseModel):
    """Represents a mapping between a bulk Excel upload and a farmer.

    This class establishes a connection between a specific bulk Excel upload
    and a farmer, indicating that the farmer's data is added through this
    upload.

    Attributes:
        upload (ForeignKey): The bulk Excel upload associated with the mapping.
        farmer (ForeignKey): The farmer associated with the mapping.
    """

    upload = models.ForeignKey(
        BulkExcelUploads,
        on_delete=models.CASCADE,
        related_name="farmer_mappings",
    )
    farmer = models.ForeignKey(
        "supply_chains.Farmer",
        on_delete=models.CASCADE,
        related_name="upload_mappings",
    )

    class Meta:
        unique_together = (
            "upload",
            "farmer",
        )

    def __str__(self):
        return f"{self.farmer.name} - Bulk upload file | {self.pk}"
