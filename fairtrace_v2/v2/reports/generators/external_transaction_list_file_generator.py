from common import datasheets
from common.datasheets.gererators import GeneratorMethod
from django.conf import settings
from v2.claims.constants import STATUS_APPROVED
from v2.claims.models import AttachedBatchClaim
from v2.products.constants import UNIT_CHOICES
from v2.products.constants import UNIT_KG
from v2.supply_chains.constants import NODE_TYPE_CHOICES
from v2.transactions.constants import EXTERNAL_TRANS_TYPE_CHOICES
from v2.transactions.constants import EXTERNAL_TRANS_TYPE_INCOMING
from v2.transactions.constants import EXTERNAL_TRANS_TYPE_OUTGOING
from v2.transactions.constants import EXTERNAL_TRANS_TYPE_REVERSAL
from v2.transactions.models import ExternalTransaction


class ExternalTransactionDataSheet(datasheets.TemplateDataGenerator):
    """Data sheet generator for ExternalTransaction list."""

    template_name = "external_txn_trace_template.xlsx"

    start_cell = (9, 2)
    created_by_cell = (3, 3)
    created_on_cell = (4, 3)
    company_cell = (5, 3)

    class Meta:
        model = ExternalTransaction
        field_map = {
            "Transaction ID": "number",
            "Supply Chain": "product__supply_chain__name",
            "Product": "product__name",
            "Quantity": "destination_quantity",
            "Transaction Type": GeneratorMethod("transaction_type"),
            "Unit": GeneratorMethod("unit"),
            "Date": "date",
            "Price": "price",
            "Currency": "currency",
            "Sender Name": "source__full_name",
            "Sender Street Name": "source__street",
            "Sender City or Village": "source__city",
            "Sender Country": "source__country",
            "Sender Province or State": "source__province",
            "Sender Postal Code": "source__zipcode",
            "Sender Type": GeneratorMethod("source_type"),
            "Receiver Name": "destination__full_name",
            "Receiver Street Name": "destination__street",
            "Receiver City or Village": "destination__city",
            "Country": "destination__country",
            "Receiver Province or State": "destination__province",
            "Receiver Postal Code": "destination__zipcode",
            "Receiver Type": GeneratorMethod("destination_type"),
            "Created On": "created_on",
            "Creator Name": "creator__name",
            "Creator Email": "creator__email",
            "Buyer Reference Number": "buyer_ref_number",
            "Seller Reference Number": "seller_ref_number",
            "Blockchain Hash": "blockchain_address",
            "Claims": GeneratorMethod("claims"),
            "Comments": "comment",
            "Trace URL": GeneratorMethod("trace_url"),
        }

    @staticmethod
    def unit(instance):
        """Returns unit."""
        try:
            return dict(UNIT_CHOICES)[int(instance.result_batch.unit)]
        except Exception as e:
            return UNIT_KG

    @staticmethod
    def source_type(instance):
        """Returns source type."""
        unit = dict(NODE_TYPE_CHOICES)[int(instance.source.type)]

    @staticmethod
    def destination_type(instance):
        """Returns destination type."""
        return dict(NODE_TYPE_CHOICES)[int(instance.destination.type)]

    @staticmethod
    def trace_url(instance):
        """Returns Trace URL."""
        link = (
            f"{settings.FRONT_ROOT_URL}/transaction-detail/external"
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

    def transaction_type(self, instance):
        """Returns transaction type."""
        choices = dict(EXTERNAL_TRANS_TYPE_CHOICES)

        # returns saved transaction_type if node is not available.
        # probably request made by an admin.
        if not self.instance.node:
            return choices[instance.type]

        if instance.type != EXTERNAL_TRANS_TYPE_REVERSAL:
            if self.instance.node != instance.source:
                return choices[EXTERNAL_TRANS_TYPE_INCOMING]
            return choices[EXTERNAL_TRANS_TYPE_OUTGOING]

        return choices[EXTERNAL_TRANS_TYPE_REVERSAL]
