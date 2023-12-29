from common import datasheets
from common.datasheets.gererators import GeneratorMethod
from django.conf import settings
from v2.claims.constants import STATUS_APPROVED
from v2.claims.models import AttachedBatchClaim
from v2.products.constants import UNIT_CHOICES
from v2.products.models import Batch
from v2.supply_chains.constants import NODE_TYPE_CHOICES
from v2.supply_chains.constants import NODE_TYPE_UNKNOWN


class StokeDataSheet(datasheets.TemplateDataGenerator):
    """Data sheet generator for Batch list."""

    template_name = "stock_trace_template.xlsx"

    start_cell = (9, 2)
    created_by_cell = (3, 3)
    created_on_cell = (4, 3)
    company_cell = (5, 3)

    class Meta:
        model = Batch
        field_map = {
            "Stoke ID": "number",
            "Supply Chain": "product__supply_chain__name",
            "Product": "product__name",
            "Initial Quantity": "initial_quantity",
            "Available Quantity": "current_quantity",
            "Unit": GeneratorMethod("unit"),
            "Created On": "created_on",
            "Create By": "sourced_by",
            "Source Name": "sourced_from__full_name",
            "Source Street Name": "sourced_from__street",
            "Source City or Village": "sourced_from__city",
            "Source Country": "sourced_from__country",
            "Source Province or State": "sourced_from__province",
            "Source Postal Code": "sourced_from__zipcode",
            "Source Type": GeneratorMethod("source_type"),
            "Buyer Reference No": "buyer_ref_number",
            "Seller Reference No": "seller_ref_number",
            "Creator Name": "creator__name",
            "Creator Email": "creator__email",
            "Blockchain Hash": "source_transaction__blockchain_address",
            "Claims": GeneratorMethod("claims"),
            "Comments": "note",
            "Trace URL": GeneratorMethod("trace_url"),
        }

    @staticmethod
    def unit(instance):
        """Returns unit."""
        return dict(UNIT_CHOICES)[int(instance.unit)]

    @staticmethod
    def source_type(instance):
        """Returns source type."""
        node_choice_data = dict(NODE_TYPE_CHOICES)
        return (
            node_choice_data[int(instance.sourced_from.type)]
            if instance.sourced_from
            else node_choice_data[NODE_TYPE_UNKNOWN]
        )

    @staticmethod
    def trace_url(instance):
        """Returns Trace URL."""
        link = f"{settings.FRONT_ROOT_URL}/stock-detail/{instance.idencode}/"
        return f'=HYPERLINK("{link}", "Batch Details (Trace)")'

    @staticmethod
    def claims(instance):
        """Returns claims."""
        attached_claims = AttachedBatchClaim.objects.filter(
            batch=instance, status=STATUS_APPROVED
        )
        return ", ".join(attached_claims.values_list("claim__name", flat=True))
