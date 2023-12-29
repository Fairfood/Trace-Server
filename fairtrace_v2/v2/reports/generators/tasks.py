import time

from celery.task import task
from django.apps import apps
from sentry_sdk import capture_exception

from v2.reports.constants import ADMIN_COMPANY
from v2.reports.constants import ADMIN_EXTERNAL_TRANSACTION
from v2.reports.constants import ADMIN_FARMER
from v2.reports.constants import COMPANY
from v2.reports.constants import COMPLETED
from v2.reports.constants import CONNECTIONS
from v2.reports.constants import EXTERNAL_TRANSACTION
from v2.reports.constants import FAILED
from v2.reports.constants import FARMER
from v2.reports.constants import INTERNAL_TRANSACTION
from v2.reports.constants import PAYMENTS
from v2.reports.constants import STOCK
from v2.reports.generators import AdminCompanyDataSheet
from v2.reports.generators import AdminFarmerDataSheet
from v2.reports.generators import ExternalTransactionDataSheet
from v2.reports.generators import InternalTransactionDataSheet
from v2.reports.generators import NodeDataSheet
from v2.reports.generators import PaymentDataSheet
from v2.reports.generators import StokeDataSheet

DATA_SHEET_CLASS = {
    STOCK: StokeDataSheet,
    EXTERNAL_TRANSACTION: ExternalTransactionDataSheet,
    INTERNAL_TRANSACTION: InternalTransactionDataSheet,
    CONNECTIONS: NodeDataSheet,
    COMPANY: NodeDataSheet,
    FARMER: NodeDataSheet,
    ADMIN_COMPANY: AdminCompanyDataSheet,
    ADMIN_FARMER: AdminFarmerDataSheet,
    ADMIN_EXTERNAL_TRANSACTION: ExternalTransactionDataSheet,
    PAYMENTS: PaymentDataSheet,
}

BUFFER = 5  # Putting a buffer in response time.


@task(name="generate_file", queue="high")
def generate_file(instance_id, pks, model, app, file_name):
    """Generate file according to the template and type."""
    st = time.time()
    export_model = apps.get_model("reports", "Export")
    qs_model = apps.get_model(app, model)
    instance = export_model.objects.get(id=instance_id)
    queryset = qs_model.objects.filter(pk__in=pks)
    try:
        data_sheet = DATA_SHEET_CLASS[instance.export_type](instance)
        data_sheet.to_sheet(queryset)
        data_sheet.save_to_instance(file_name)
        data_sheet.close()
    except Exception as err:
        instance.status = FAILED
        instance.save(update_fields=["status"])
        capture_exception(err)
    et = time.time() - st
    instance.status = COMPLETED
    instance.atc = round(et) + BUFFER
    instance.save(update_fields=["status", "atc", "file"])
