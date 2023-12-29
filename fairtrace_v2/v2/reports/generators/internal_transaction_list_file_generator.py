from common import datasheets
from common.datasheets.gererators import GeneratorMethod
from django.conf import settings
from v2.claims.constants import STATUS_APPROVED
from v2.claims.models import AttachedBatchClaim
from v2.products.constants import UNIT_CHOICES
from v2.transactions.constants import INTERNAL_TRANS_TYPE_CHOICES
from v2.transactions.models import InternalTransaction


class InternalTransactionDataSheet(datasheets.TemplateDataGenerator):
    """Data sheet generator for InternalTransactions list."""

    template_name = "stock_actions_trace_template.xlsx"

    start_cell = (9, 2)
    created_by_cell = (3, 3)
    created_on_cell = (4, 3)
    company_cell = (5, 3)

    class Meta:
        model = InternalTransaction
        field_map = {
            "Transaction ID": "number",
            "Supply Chain": "product__supply_chain__name",
            "Source Products": "source_products__name",
            "Source Quantity": "source_quantity",
            "Destination products": "destination_products__name",
            "Destination Quantity": "destination_quantity",
            "Type": GeneratorMethod("transaction_type"),
            "Unit": GeneratorMethod("unit"),
            "Date": "date",
            "Created On": "created_on",
            "Creator Name": "creator__name",
            "Creator Email": "creator__email",
            "Blockchain Hash": "blockchain_address",
            "Claims": "result_batches__claims__claim__name",
            "Comments": "comment",
            "Trace URL": GeneratorMethod("trace_url"),
        }

    @staticmethod
    def unit(instance):
        """Returns unit."""
        return dict(UNIT_CHOICES)[int(instance.first_source_batch.unit)]

    @staticmethod
    def trace_url(instance):
        """Returns Trace URL."""
        link = (
            f"{settings.FRONT_ROOT_URL}/transaction-detail/internal"
            f"/{instance.idencode}/"
        )
        return f'=HYPERLINK("{link}", "Transaction Details (Trace)")'

    @staticmethod
    def claims(instance):
        """Returns claims."""
        attached_claims = AttachedBatchClaim.objects.filter(
            batch__in=instance.result_batches.all(), status=STATUS_APPROVED
        )
        return ", ".join(attached_claims.values_list("claim__name", flat=True))

    @staticmethod
    def transaction_type(instance):
        """Returns transaction type."""
        return dict(INTERNAL_TRANS_TYPE_CHOICES)[int(instance.type)]
