from common import datasheets
from common.datasheets.gererators import GeneratorMethod
from django.conf import settings
from django.db.models import Q
from v2.supply_chains.constants import NODE_STATUS_ACTIVE
from v2.supply_chains.constants import NODE_TYPE_CHOICES
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Company
from v2.supply_chains.models import Connection
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Node
from v2.transactions.models import ExternalTransaction


class NodeDataSheet(datasheets.TemplateDataGenerator):
    """Data sheet generator for Connection list."""

    template_name = "connections_trace_template.xlsx"

    start_cell = (9, 2)
    created_by_cell = (3, 3)
    created_on_cell = (4, 3)
    company_cell = (5, 3)

    class Meta:
        model = Node
        field_map = {
            "Create On": "created_on",
            "Number of Farmers connected": GeneratorMethod(
                "connected_farmer_count"
            ),
            "Number of Companies connected": GeneratorMethod(
                "connected_company_count"
            ),
            "Number of Active supply chains": GeneratorMethod(
                "active_supply_chain_count"
            ),
            "Transaction Count": GeneratorMethod("transaction_count"),
            "Status": GeneratorMethod("status"),
            "Type": GeneratorMethod("node_type"),
            "Date of Join": GeneratorMethod("date_joined"),
            "Creator Name": "creator__name",
            "Creator Email": "creator__email",
            "Name": "full_name",
            "Street Name": "street",
            "Country": "country",
            "Province": "province",
            "City/Village": "city",
            "Phone number": "phone_number",
            "Postel Code": "zipcode",
            "Trace URL": GeneratorMethod("trace_url"),
        }

    @staticmethod
    def node_type(instance):
        """Returns Node type."""
        return dict(NODE_TYPE_CHOICES)[int(instance.type)]

    @staticmethod
    def date_joined(instance):
        """Returns joined date."""
        date = instance.date_joined or instance.created_on
        return date.date()

    @staticmethod
    def trace_url(instance):
        """Returns Trace URL."""
        link = (
            f"{settings.FRONT_ROOT_URL}/connections/profile/company"
            f"/{instance.idencode}/"
        )
        return f'=HYPERLINK("{link}", "Connection Details (Trace)")'

    @staticmethod
    def status(instance):
        """Returns Status."""
        email_sent = instance.email_sent
        status = instance.status
        if not email_sent:
            return "Mapped(Not invited)"
        if status != NODE_STATUS_ACTIVE:
            return "Invited"
        return "Verified"

    @staticmethod
    def transaction_count(instance):
        """Returns transaction count."""
        node = instance
        qs = ExternalTransaction.objects.filter(
            Q(source=node) | Q(destination=node)
        )
        return qs.count()

    def connected_farmer_count(self, instance):
        """Returns connected farmers count."""
        qs = self._get_connections("FARMER", instance)
        return qs.count()

    def connected_company_count(self, instance):
        """Returns connected company count."""
        qs = self._get_connections("COMPANY", instance)
        return qs.count()

    @staticmethod
    def active_supply_chain_count(instance):
        """Returns active supply-chain count."""
        return (
            instance.supply_chains.filter(active=True)
            .order_by("name")
            .distinct("name")
            .count()
        )

    @staticmethod
    def _get_connections(_type, instance):
        """To perform function _get_connections."""
        if _type == "COMPANY":
            return Connection.objects.filter(
                Q(buyer=instance, supplier__type=NODE_TYPE_COMPANY)
                | Q(supplier=instance, buyer__type=NODE_TYPE_COMPANY)
            )
        elif _type == "FARMER":
            return Connection.objects.filter(
                Q(buyer=instance, supplier__type=NODE_TYPE_FARM)
                | Q(supplier=instance, buyer__type=NODE_TYPE_FARM)
            )
        else:
            return Connection.objects.filter(
                Q(buyer=instance) | Q(supplier=instance)
            )


class AdminCompanyDataSheet(NodeDataSheet):
    """Sub-classing NodeDataSheet for handling Company specific ops."""

    class Meta(NodeDataSheet.Meta):
        model = Company


class AdminFarmerDataSheet(NodeDataSheet):
    """Sub-classing NodeDataSheet for handling Company specific ops."""

    class Meta(NodeDataSheet.Meta):
        model = Farmer
