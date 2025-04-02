"""Base Node model for both company and farmer."""
import json

from common import library as comm_lib
from common.country_data import DIAL_CODE_NAME_MAP
from common.library import _get_file_path
from common.models import AbstractBaseModel, Address
from django.core.exceptions import (MultipleObjectsReturned,
                                    ObjectDoesNotExist, ValidationError)
from django.db import models, transaction
from django.utils import timezone
from django_extensions.db.fields.json import JSONField
from v2.accounts.models import FairfoodUser
from v2.supply_chains import constants
from v2.transactions.models import Transaction

from ...products.models import Product
from ...projects.models import Project
from ..constants import INVITE_RELATION_BUYER, INVITE_RELATION_SUPPLIER
from ..managers import NodeQuerySet
from .cypher import START_CONN, TAGS
from .graph import NodeGraphModel

# Create your models here.


class Node(AbstractBaseModel, Address):
    """Base model for every type of nodes.

    Attributes:
        external_id(str): External ID of the Node (from Connect server).
        type(int[choice]): Type of the Node (Company of Farmer)
        profile_mode(int[choice]): Profile modes can be Network or Transaction.
        identification_no(str): Legal Identification/Registration no of the
                                node.
        registration_date(date): Legal Registration date.
        email(str): Email ID associated with the Node.
        phone(str): Phone number associated with the Node.
        description_basic(str): Basic description
        description_full(str): Complete description
        image(image): Node Image/Logo
        disclosure_level(int[choice]):  Disclosure level setting.
                                        Can be Full/Custom
        visible_fields(list(chars)):  List of fields to disclose.
        date_invited(date): Date when the Node was invited to Fairfood.
        date_joined(date): Date when the Node joined Fairfood.
        status(int[choices]): The profile status of the node.
                              Shows the completion status of profile.
        verified(bool): If the Node is verified or not.
        blockchain_account(obj): Connection to Blockchain account details.
                                  Will be empty if blockchain account has not
                                  been setup.
        primary_operation(obj): Primary operation of the Node.
        other_operations(obj): Other operations of the Node.

    Inherited Attributes:
        house_name(str) : Address field
        street(str) : Address field
        city(str) : Address field
        province(str) : Address field
        country(str) : Address field
        latitude(str) : Address field
        longitude(str) : Address field
        zipcode(str) : Address field
    """
    external_id = models.CharField(max_length=100, null=True, blank=True)
    navigate_id = models.CharField(max_length=100, null=True, blank=True)
    sso_id = models.CharField(max_length=100, null=True, blank=True)
    graph_uid = models.CharField(max_length=100, null=True, blank=True)
    type = models.IntegerField(choices=constants.NODE_TYPE_CHOICES)
    profile_mode = models.IntegerField(
        choices=constants.NODE_PROFILE_MODE_CHOICES,
        default=constants.PROFILE_MODE_NETWORK,
    )
    identification_no = models.CharField(
        max_length=500, blank=True, default=""
    )
    registration_date = models.DateField(null=True, blank=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=50, default="", blank=True)
    description_basic = models.CharField(
        max_length=500, default="", blank=True
    )
    description_full = models.CharField(
        max_length=2000, default="", blank=True
    )
    image = models.ImageField(
        upload_to=_get_file_path, null=True, default=None, blank=True
    )
    disclosure_level = models.IntegerField(
        choices=constants.NODE_DISCLOSURE_CHOICES,
        default=constants.NODE_DISCLOSURE_CUSTOM,
    )
    visible_fields = models.CharField(max_length=1000, default="{}")
    date_invited = models.DateTimeField(null=True, blank=True, default=None)
    date_joined = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(
        choices=constants.NODE_STATUS_CHOICES,
        default=constants.NODE_STATUS_INACTIVE,
    )
    verified = models.BooleanField(default=False)
    blockchain_account = models.OneToOneField(
        "supply_chains.BlockchainWallet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="old_node",
    )
    blockchain_address = models.CharField(
        max_length=200, default="", null=True, blank=True
    )
    primary_operation = models.ForeignKey(
        "supply_chains.Operation",
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
        related_name="primary_nodes",
    )
    other_operations = models.ManyToManyField(
        "supply_chains.Operation",
        related_name="secondary_nodes",
        default=None,
        blank=True,
    )
    selected_theme = models.IntegerField(
        choices=constants.SELECTED_THEME_CHOICES,
        default=constants.SELECTED_THEME_DEFAULT,
    )

    managers = models.ManyToManyField(
        "self",
        through="supply_chains.NodeManager",
        symmetrical=False,
        related_name="nodes_managed",
        through_fields=("node", "manager"),
    )

    suppliers = models.ManyToManyField(
        "self",
        through="Connection",
        symmetrical=False,
        related_name="buyers",
        through_fields=("buyer", "supplier"),
    )
    members = models.ManyToManyField(
        "accounts.FairfoodUser",
        through="NodeMember",
        related_name="nodes",
        through_fields=("node", "user"),
    )
    supply_chains = models.ManyToManyField(
        "supply_chains.SupplyChain",
        through="NodeSupplyChain",
        related_name="nodes",
    )
    products = models.ManyToManyField(
        "products.Product", through="products.Batch", related_name="actors"
    )
    verifier_supply_chains = models.ManyToManyField(
        "supply_chains.SupplyChain",
        through="supply_chains.Verifier",
        related_name="verifiers",
    )
    plan = models.IntegerField(
        choices=constants.NODE_PLAN_CHOICES, default=constants.NODE_PLAN_BASIC
    )
    is_test = models.BooleanField(default=False)
    app_custom_fields = JSONField(blank=True, null=True)

    buy_enabled = models.BooleanField(default=True)
    sell_enabled = models.BooleanField(default=False)
    quality_correction = models.BooleanField(default=False)
    show_price_comparison = models.BooleanField(default=True)

    objects = NodeQuerySet.as_manager()

    class Meta:
        ordering = ("id",)

    def clean(self):
        """Performs additional cleaning/validation for the Node instance.

        This method overrides the parent's clean method to include
        additional logic. It ensures that the 'street' and 'city' fields
        are properly capitalized.
        """
        super(Node, self).clean()
        if self.street:
            self.street = str(self.street).title()
        if self.city:
            self.cit = str(self.city).title()

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        super(Node, self).__init__(*args, **kwargs)
        if not self.pk:
            visible_fields = {}
            for field in constants.VISIBLE_FIELDS[self.type].keys():
                visible_fields[field] = False
            self.visible_fields = json.dumps(visible_fields)

    def __str__(self):
        """To perform function __str__."""
        return "%s : %s | %s" % (
            self.full_name,
            self.get_type_display(),
            self.id,
        )

    def save(self, *args, **kwargs):
        """Save override for pre-save."""
        super(Node, self).save(*args, **kwargs)
        self.full_clean()
        transaction.on_commit(lambda: self.create_or_update_graph_node())
        from v2.supply_chains.cache_resetters import reload_related_statistics

        transaction.on_commit(lambda: reload_related_statistics.delay(self.pk))
        transaction.on_commit(lambda: self.update_cache())

    def get_primary_operation(self, batch):
        """Get primary operation details from the transaction node."""
        nsc = self.nodesupplychain_set.filter(
            supply_chain=batch.instance.product.supply_chain
        ).first()
        if not nsc:
            nsc = self.nodesupplychain_set.last()
        primary_operation = {
            "id": nsc.primary_operation.idencode,
            "name": nsc.primary_operation.name,
        }
        return primary_operation

    @property
    def graph_node(self):
        """Returns graph node."""
        if not self.graph_uid:
            return None
        return NodeGraphModel.nodes.get_or_none(uid=self.graph_uid)

    def create_or_update_graph_node(self):
        """Create or updated graph node."""
        graph_node = self.graph_node
        if not graph_node:
            graph_node = NodeGraphModel(
                ft_node_id=self.id,
                ft_node_idencode=self.idencode,
                type=self.type,
                full_name=self.full_name,
            )
            graph_node.save()
            self.graph_uid = graph_node.uid
            self.save()

        managers = [
            {"id": i.idencode, "name": i.full_name}
            for i in self.managers.all()
        ]
        graph_node.full_name = self.full_name
        graph_node.managers = managers
        graph_node.save()

    @property
    def node_object(self):
        """Returns node object."""
        if self.type == constants.NODE_TYPE_COMPANY:
            return self.company
        elif self.type == constants.NODE_TYPE_FARM:
            return self.farmer
        raise ValidationError(f"Invalid node type choice for {self}")

    def is_farm(self):
        """check if it is a farmer."""
        if self.type == constants.NODE_TYPE_FARM:
            return True
        return False

    def is_company(self):
        """Check if it is a company."""
        if self.type == constants.NODE_TYPE_COMPANY:
            return True
        return False

    @property
    def full_name(self):
        """Returns full name."""
        return self.node_object.name

    @property
    def primary_operation_name(self):
        """To perform function primary_operation_name."""
        nsc = self.nodesupplychain_set.filter(
            supply_chain=self.supply_chains.all().first()
        ).last()
        if not nsc:
            return ""
        return nsc.primary_operation.name

    @property
    def dial_code(self):
        """Returns dial code."""
        code, phone = comm_lib._split_phone(self.phone)
        return code

    @property
    def dial_code_text(self):
        """Returns dial-code text."""
        return DIAL_CODE_NAME_MAP.get(self.dial_code, "")

    @property
    def phone_number(self):
        """returns phone number."""
        code, phone = comm_lib._split_phone(self.phone)
        return phone

    @property
    def short_name(self):
        """Returns short_name."""
        return self.node_object.short_name

    @property
    def email_sent(self):
        """Check email is sent."""
        if self.invitations_received.filter(email_sent=True).exists():
            return True
        if not self.invitations_received.all().exists():
            return True
        return False

    def get_latlong(self):
        """Get latlong as dict."""
        return {"latitude": self.latitude, "longitude": self.longitude}

    @property
    def incharge_user(self):
        """Returns in-charge user."""
        if self.type == constants.NODE_TYPE_COMPANY:
            return self.company.incharge.get_or_create_user()
        elif self.type == constants.NODE_TYPE_FARM:
            return self.farmer.get_or_create_user()

    def can_manage(self, node, supply_chain=None):
        """If a connection for a particular node can be added by self."""
        if type(node) != Node:
            node = node.node_ptr
        if node == self:
            return True
        if self in node.managers.all():
            return True
        if node in self.get_suppliers(supply_chain=supply_chain):
            return True
        if node in self.get_buyers(supply_chain=supply_chain):
            return True
        invitations = self.invitations_sent.filter(invitee=node)
        if supply_chain:
            invitations = invitations.filter(
                connection__supply_chain=supply_chain
            )
        if invitations.exists():
            return True
        return False

    def get_managed_nodes(self, supply_chain=None):
        """Returns queryset of nodes that are managed by self."""
        managed_nodes = Node.objects.filter(id=self.id)
        managed_nodes = managed_nodes.union(self.nodes_managed.all())
        managed_nodes = managed_nodes.union(
            self.get_suppliers(supply_chain=supply_chain)
        )
        managed_nodes = managed_nodes.union(
            self.get_buyers(supply_chain=supply_chain)
        )
        managed_nodes = managed_nodes.union(
            Node.objects.filter(
                # All nodes that you've invited in this supply chain
                invitations_received__inviter=self,
                invitations_received__connection__supply_chain=supply_chain,
            )
        )
        return managed_nodes

    def can_read(self, node, supply_chain=None):
        """If a particular node can be read by self."""
        if node.disclosure_level == constants.NODE_DISCLOSURE_FULL:
            return True
        return self.can_manage(node, supply_chain)

    @property
    def image_url(self):
        """returns image url."""
        if self.image:
            return self.image.url
        else:
            return ""

    def update_date_joined(self):
        """Update date joined."""
        if not self.date_joined:
            self.stats.outdate()
            self.date_joined = timezone.now()
            self.status = constants.NODE_STATUS_ACTIVE
            if self.type == constants.NODE_TYPE_COMPANY:
                self.node_manager_objects.all().delete()
            self.save()
            self.create_or_update_graph_node()
            self.verify_connections()
            transaction.on_commit(lambda: self.update_cache())
            from v2.supply_chains.cache_resetters import \
                reload_related_statistics

            transaction.on_commit(
                lambda: reload_related_statistics.delay(self.id)
            )

    def get_hidden_fields(self):
        """returns hidden fields."""
        if self.disclosure_level == constants.NODE_DISCLOSURE_FULL:
            hidden_fields = []
        else:
            custom_settings = json.loads(self.visible_fields)
            hidden_fields = []
            for field, visible in custom_settings.items():
                if not visible:
                    if isinstance(
                        constants.VISIBLE_FIELDS[self.type][field], dict
                    ):
                        fields: dict = constants.VISIBLE_FIELDS[self.type][
                            field
                        ]
                        hidden_fields += list(fields.keys())
                    else:
                        hidden_fields.append(field)
        return hidden_fields

    def verify_connections(self):
        """Verify connections."""
        for connection in self.buyer_connections.all():
            connection.verify_connection()
            connection.update_graph_node()
        for connection in self.supplier_connections.all():
            connection.verify_connection()
            connection.update_graph_node()

    @property
    def subscribers(self):
        """Return subscribers."""
        from v2.supply_chains.models import NodeMember

        node_members = NodeMember.objects.filter(
            node=self,
            type__in=[
                constants.NODE_MEMBER_TYPE_ADMIN,
                constants.NODE_MEMBER_TYPE_MEMBER,
            ],
        )
        if self.date_joined:
            node_members = node_members.filter(active=True)
        elif self.is_company():
            from v2.supply_chains.models import NodeMember

            user = self.company.incharge.get_or_create_user()
            member, created = NodeMember.objects.get_or_create(
                node=self, user=user
            )
            if created:
                member.type = constants.NODE_MEMBER_TYPE_ADMIN
                member.creator = self.creator
                member.updater = self.creator
                member.save()
            node_members = [member]
        return FairfoodUser.objects.filter(usernodes__in=node_members)

    def make_member_active(self, user):
        """make member active."""
        member = self.nodemembers.get(user=user)
        member.active = True
        member.save(update_fields=["active"])

    @property
    def profile_completion(self):
        """check if profile completed."""
        return self.node_object.profile_completion

    def get_connections(self, supply_chain=None):
        """Returns connections."""
        my_connections = self.get_buyers(
            supply_chain=supply_chain
        ) | self.get_suppliers(supply_chain=supply_chain)
        return my_connections.distinct("id")

    def get_products(self, supply_chain=None):
        """Returns products."""
        products = self.products.order_by("id").distinct("id")
        if supply_chain:
            products = products.filter(supply_chain=supply_chain)
        return products

    def is_supplier(self, node, supply_chain=None):
        """check is supplier."""
        supplier_connections = node.supplier_connections.filter(supplier=self)
        if supply_chain:
            supplier_connections = supplier_connections.filter(
                supply_chain=supply_chain
            )
        return supplier_connections.exists()

    def is_buyer(self, node, supply_chain=None):
        """check is buyer."""
        buyer_connections = node.buyer_connections.filter(buyer=self)
        if supply_chain:
            buyer_connections = buyer_connections.filter(
                supply_chain=supply_chain
            )
        return buyer_connections.exists()

    def is_directly_connected_to(self, node, supply_chain=None):
        """check if directly connected to."""
        return self.is_supplier(
            node, supply_chain=supply_chain
        ) or self.is_buyer(node, supply_chain=supply_chain)

    def get_buyers(self, supply_chain=None, parent=None):
        """Return all buyers as queryset with an option to filter by supply
        chain."""
        buyer_connections = self.buyer_connections.all()
        if supply_chain:
            buyer_connections = self.buyer_connections.filter(
                supply_chain=supply_chain
            )
        if parent:
            buyer_connections = buyer_connections.filter(
                supplier_tags__supplier_connection__supplier=parent
            )
        buyers = self.buyers.filter(supplier_connections__in=buyer_connections)
        return buyers

    def get_suppliers(self, supply_chain=None, parent=None):
        """Return all suppliers as queryset with an option to filter by supply
        chain."""
        supplier_connections = self.supplier_connections.all()
        if supply_chain:
            supplier_connections = supplier_connections.filter(
                supply_chain=supply_chain
            )
        if parent:
            supplier_connections = supplier_connections.filter(
                buyer_tags__buyer_connection__buyer=parent
            )
        suppliers = self.suppliers.filter(
            buyer_connections__in=supplier_connections
        )
        return suppliers

    def get_t2_suppliers(self, through=None, supply_chain=None):
        """Returns t2 suppliers."""
        supplier_connections = self.supplier_connections.filter()
        if through:
            supplier_connections = supplier_connections.filter(
                supplier=through
            )
        if supply_chain:
            supplier_connections = supplier_connections.filter(
                supply_chain=supply_chain
            )
        _key = "buyer_connections__buyer_tags__buyer_connection__in"
        _filter_dict = {_key: supplier_connections}
        return Node.objects.filter(**_filter_dict)

    def get_t2_buyers(self, through=None, supply_chain=None):
        """Returns t2 buyers."""
        buyer_connections = self.buyer_connections.filter()
        if through:
            buyer_connections = buyer_connections.filter(buyer=through)
        if supply_chain:
            buyer_connections = buyer_connections.filter(
                supply_chain=supply_chain
            )
        _key = "supplier_connections__supplier_tags__supplier_connection__in"
        _filter_dict = {_key: buyer_connections}
        return Node.objects.filter(**_filter_dict)

    def get_buyer_chain(
        self,
        supply_chain=None,
        include_self=False,
        fast_mode=False,
        labels=None,
    ):
        """Returns buyer chain."""
        start_connections = None
        if labels:
            start_connections = self.buyer_connections.filter(
                labels__in=labels
            )
            if supply_chain:
                start_connections = start_connections.filter(
                    supply_chain=supply_chain
                )
        if not self.graph_node:
            return [], {}
        chain_node_ids, tied_data = self.graph_node.get_buyer_chain(
            supply_chain, include_self, fast_mode, start_connections
        )
        chain_nodes = Node.objects.filter(id__in=chain_node_ids)
        return chain_nodes, tied_data

    def get_supplier_chain(
        self,
        supply_chain=None,
        include_self=False,
        fast_mode=False,
        labels=None,
    ):
        """Returns supplier chain."""
        start_connections = None
        if labels:
            start_connections = self.supplier_connections.filter(
                labels__in=labels
            )
            if supply_chain:
                start_connections = start_connections.filter(
                    supply_chain=supply_chain
                )
        chain_node_ids, tied_data = self.graph_node.get_supplier_chain(
            supply_chain, include_self, fast_mode, start_connections
        )
        chain_nodes = Node.objects.filter(id__in=chain_node_ids)
        return chain_nodes, tied_data

    def map_supplier_pks(self, supply_chain=None, start_connections=None):
        """Returns a list of supplier pks in the order of the supply chain."""
        data = self.graph_node.map_suppliers(supply_chain, start_connections)
        return tuple(item[0].get("ft_node_id") for item in data)

    def map_buyer_pks(self, supply_chain=None, start_connections=None):
        """Returns a list of buyer pks in the order of the supply chain."""
        data = self.graph_node.map_buyers(supply_chain, start_connections)
        return tuple(item[0].get("ft_node_id") for item in data)

    def get_tier(
        self, supply_chain=None, start_connections=None, target_node=None
    ):
        """Returns tier."""
        connection_type, tier = None, 0
        data = self.graph_node.map_suppliers(
            supply_chain, start_connections, target_node=target_node
        )
        if data:
            tier = -(len(data[0][TAGS]) + 1)
            connection_type = INVITE_RELATION_SUPPLIER
        if tier == 0:
            data = self.graph_node.map_buyers(
                supply_chain, start_connections, target_node=target_node
            )
            if data:
                tier = len(data[0][TAGS]) + 1
                connection_type = INVITE_RELATION_BUYER
        try:
            status = data[0][START_CONN]["status"]
        except (IndexError, KeyError, TypeError) as e:
            status = None 

        return tier, connection_type, status

    def get_chain(self, supply_chain=None, include_self=True):
        """Returns chain."""
        suppliers, supplier_tier_data = self.get_supplier_chain(
            supply_chain=supply_chain, include_self=include_self
        )
        buyers, buyer_tier_data = self.get_buyer_chain(
            supply_chain=supply_chain
        )

        return comm_lib._combine_queries(suppliers, buyers)

    def get_transactions(self):
        """Returns transactions."""
        external = (
            self.incoming_transactions.all() | self.outgoing_transactions.all()
        )
        transactions = Transaction.objects.filter(
            externaltransaction__in=external
        )
        transactions |= Transaction.objects.filter(
            internaltransaction__in=self.internaltransactions.all()
        )
        return transactions.order_by().distinct("id")

    def get_actions(self):
        """Returns actions."""
        actions = []
        profile_completion = self.profile_completion
        if profile_completion < 100:
            actions.append(
                {
                    "type": constants.NODE_ACTION_COMPLETE_PROFILE,
                    "text": "{0}% of your profile is completed.".format(
                        int(profile_completion)
                    ),
                    "action_text": "Complete Profile",
                }
            )
        for supply_chain in self.supply_chains.all():
            if not self.invitations_sent.filter(
                connection__supply_chain=supply_chain
            ):
                txt = "You have been invited to {0} supply chain."
                actions.append(
                    {
                        "type": constants.NODE_ACTION_INVITE_ACTORS,
                        "text": (txt.format(supply_chain.name)),
                        "action_text": "Invite connections",
                        "supply_chain": supply_chain.idencode,
                    }
                )
        return actions

    def get_theme_data(self):
        """Returns theme data."""
        themes = []
        for theme in self.themes.all():
            batch_id = theme.batch.idencode if theme.batch else ""
            themes.append(
                {
                    "id": theme.idencode,
                    "name": theme.name,
                    "batch": batch_id,
                }
            )
        return themes

    @property
    def hedera_wallet(self):
        """Returns headera wallet."""
        return self.wallets.filter(
            wallet_type=constants.BLOCKCHAIN_WALLET_TYPE_HEDERA, default=True
        ).first()

    def setup_blockchain_account(self, reset=False):
        """To set-up bc account."""
        hedera_wallets = self.wallets.filter(
            wallet_type=constants.BLOCKCHAIN_WALLET_TYPE_HEDERA, default=True
        )
        if hedera_wallets.exists() and not reset:
            return hedera_wallets.first()

        for wallet in self.wallets.all():
            wallet.disable()

        from .profile import BlockchainWallet

        bc_account = BlockchainWallet.objects.create(node=self, default=True)
        bc_account.create_blockchain_account()
        return bc_account

    def retry_pending_blockchain_actions(self):
        """Retries the pending bc actions."""
        if self.is_farm():
            for batch in self.batches.all():
                batch.create_blockchain_asset()
        for trans in self.incoming_transactions.all():
            trans.log_blockchain_transaction()
        # Outgoing transaction will be logged when the incoming transaction
        # hash is received
        return True

    @property
    def blockchain_wallet(self):
        """Returns the bc wallet."""
        try:
            return self.wallets.get(default=True)
        except MultipleObjectsReturned:
            raise AssertionError("Multiple default wallets found")
        except ObjectDoesNotExist:
            raise AssertionError("Wallet not found")

    @property
    def blockchain_key(self):
        """Returns the bc key."""
        if self.blockchain_address:
            return self.blockchain_address
        if not self.blockchain_account or not self.blockchain_account.public:
            return ""
        address = self.blockchain_account.public
        self.blockchain_address = address
        self.save()
        return

    def update_cache(self):
        """Update the cache."""
        from v2.supply_chains.serializers.functions import (
            serialize_node_basic, serialize_node_blockchain)

        serialize_node_basic(self, force_reload=True)
        serialize_node_blockchain(self, force_reload=True)
        return True

    @property
    def unique_products(self):
        """Get unique products."""
        app_projects = Project.objects.filter(
            member_objects__node=self
        ).values("id")
        app_products = Product.objects.filter(
            project_objects__project_id__in=app_projects
        )
        products = app_products | self.products.all()
        return products.distinct()

    def search_suppliers(self, target_node, supply_chain=None):
        """To search suppliers."""
        from v2.supply_chains.models import Connection

        connections = self.graph_node.search_suppliers(
            target_node.graph_node, supply_chain
        )
        for connection in connections:
            sc_id = connection.pop("supply_chain_id")
            connection_id = connection.pop("connection_id")
            connection["supply_chain"] = self.supply_chains.get(id=sc_id)
            connection["connection"] = Connection.objects.get(id=connection_id)
            path = []
            for actor_id in connection["path"]:
                path.append(Node.objects.get(id=actor_id))
            connection["path"] = path
            connection["tier"] = len(path) - 1

        return connections

    def search_buyers(self, target_node, supply_chain=None):
        """To search buyyers."""
        from v2.supply_chains.models import Connection

        connections = self.graph_node.search_buyers(
            target_node.graph_node, supply_chain
        )
        for connection in connections:
            sc_id = connection.pop("supply_chain_id")
            connection_id = connection.pop("connection_id")
            connection["supply_chain"] = self.supply_chains.get(id=sc_id)
            connection["connection"] = Connection.objects.get(id=connection_id)
            path = []
            for actor_id in connection["path"]:
                path.append(Node.objects.get(id=actor_id))
            connection["path"] = path
            connection["tier"] = -(len(path) - 1)

        return connections

    def search_node(self, target_node, supply_chain=None):
        """To search nodes."""
        buyer_search = self.search_buyers(
            target_node=target_node, supply_chain=supply_chain
        )
        supplier_search = self.search_suppliers(
            target_node=target_node, supply_chain=supply_chain
        )
        return buyer_search + supplier_search

    @property
    def supply_chain_count(self):
        """Returns supply-chain count."""
        return self.supply_chains.count()

    def send_pending_invites(self):
        """Send pending invites."""
        for inv in self.invitations_received.filter(email_sent=False):
            inv.send_initial_connection_request()
            inv.email_sent = True
            inv.save()
        return True
