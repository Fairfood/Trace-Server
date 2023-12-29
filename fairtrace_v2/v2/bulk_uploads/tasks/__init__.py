from celery.task import task
from django.apps import apps
from sentry_sdk import capture_exception

from v2.bulk_templates.constants import (TEMPLATE_TYPE_TXN,
                                         TEMPLATE_TYPE_CONNECTION)
from v2.bulk_uploads.tasks.bulk_connection_adaptors import (
    BulkConnectionAdapter, )
from v2.bulk_uploads.tasks.bulk_trace_adapters import BulkTraceAdapter
from v2.bulk_uploads.tasks.bulk_transaction_adapters import (
    BulkTransactionAdapter, )


@task(name="bulk_upload", queue="low")
def bulk_upload(upload_id):
    """
    Celery task to process bulk data sheet upload.

    This task processes a bulk data sheet upload by adapting, formatting, and
    creating transaction or connection data based on the provided
    DataSheetUpload     instance.

    Parameters:
    upload_id (int): The ID of the DataSheetUpload instance to process.

    Returns:
    str: A message indicating the processing result.
    """
    # Get the DataSheetUpload model using the apps module
    data_sheet_upload_model = apps.get_model("bulk_uploads",
                                             "DataSheetUpload")

    # Retrieve the DataSheetUpload instance using the provided upload_id
    data_sheet = data_sheet_upload_model.objects.get(id=upload_id)

    # Determine the appropriate adapter based on the template type
    adapter_mapping = {
        TEMPLATE_TYPE_TXN: BulkTransactionAdapter,
        TEMPLATE_TYPE_CONNECTION: BulkConnectionAdapter,
        # Add more mappings as needed
    }

    if data_sheet.template.is_system_template:
        adapter_class = BulkTraceAdapter
    elif data_sheet.template.type in adapter_mapping:
        adapter_class = adapter_mapping[data_sheet.template.type]
    else:
        return "Unsupported template type"

    adapter = adapter_class(data_sheet)

    # Format the data from the data sheet
    adapter.format_data()

    # Create the data using the formatted data
    try:
        adapter.create_data()
    except Exception as e:
        # If there are exceptions during the processing, capture them.
        capture_exception(e)

    # If there are errors during the processing, update the data sheet
    # with errors
    if adapter.errors:
        data_sheet.errors = adapter.errors

    # If there are exceptions during the processing, capture them.
    for exception in adapter.exceptions:
        capture_exception(exception)

    # Mark the data sheet as used and save it
    data_sheet.is_used = True
    data_sheet.save()

    return (f"Processed {data_sheet.template.get_type_display()} data "
            f"sheet {data_sheet.idencode}")
