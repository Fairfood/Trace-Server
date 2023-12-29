from common import datasheets
from common.datasheets.gererators import GeneratorMethod
from v2.projects.models import Payment


class PaymentDataSheet(datasheets.TemplateDataGenerator):
    """Data sheet generator for Batch list."""

    template_name = "payments_trace_template.xlsx"

    start_cell = (9, 2)
    created_by_cell = (3, 3)
    created_on_cell = (4, 3)
    company_cell = (5, 3)

    class Meta:
        model = Payment
        field_map = {
            "Reference ID": "idencode",
            "Date": "created_on",
            "Source": "source__full_name",
            "Destination": "destination__full_name",
            "Description": "description",
            "Amount": "amount",
            "Currency": "currency",
            "Creator Name": "creator__name",
            "Creator Email": "creator__email",
            "Verification method": "method",
            "Invoice": GeneratorMethod("invoice"),
        }

    @staticmethod
    def invoice(instance):
        """Return hyperlinked invoice url."""
        if instance.invoice:
            return (
                f'=HYPERLINK("{instance.invoice.url}", '
                f'"{instance.invoice.name}")'
            )
        return None
