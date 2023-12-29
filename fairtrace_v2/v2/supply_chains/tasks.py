"""Celery tasks from Supply chain app."""
import copy
from datetime import date
from datetime import timedelta

from celery.decorators import task
from rest_framework import serializers
from sentry_sdk import capture_message
from v2.bulk_templates.models import DynamicBulkUpload
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.models import BulkExcelUploads
from v2.supply_chains.models import Invitation


@task(name="send_out_reminder_emails", queue="low")
def send_out_reminder_emails():
    """To sent reminder emails."""
    today = date.today()
    one_week_back = today - timedelta(days=7)
    two_weeks_back = today - timedelta(days=14)

    invitations = Invitation.objects.filter(
        invitee__type=NODE_TYPE_COMPANY,
        email_sent=True,
        invitee__date_joined=None,
    )
    for inv in invitations.filter(invited_on__contains=one_week_back):
        inv.send_reminder(week=1)
    for inv in invitations.filter(invited_on__contains=two_weeks_back):
        inv.send_reminder(week=2)


@task(name="upload_bulk_connection_transaction", queue="low")
def upload_bulk_connection_transaction(bulk_excel_id):
    """To upload bulk connections with transaction."""
    from v2.supply_chains.serializers.supply_chain import (
        FarmerBulkInviteSerializerAsync,
    )

    bulk_file = BulkExcelUploads.objects.get(id=bulk_excel_id)

    data = copy.deepcopy(bulk_file.data)
    data["supply_chain"] = bulk_file.supply_chain.idencode
    data["node"] = bulk_file.node
    data["user"] = bulk_file.creator
    ser = FarmerBulkInviteSerializerAsync(
        data=data,
        context={
            "node": bulk_file.node,
            "user": bulk_file.creator,
            "bulk_file": bulk_file,
        },
    )
    if not ser.is_valid():
        bulk_file.errors = ser.errors
        bulk_file.save()
        capture_message(
            "Serialization errors in bulk upload.", level="critical"
        )
        raise serializers.ValidationError(ser.errors)
    resp = ser.save()
    bulk_file.farmers_to_add = resp["farmers_to_add"]
    bulk_file.farmers_added = resp["farmers_added"]
    bulk_file.farmers_to_update = resp["farmers_to_update"]
    bulk_file.farmers_updated = resp["farmers_updated"]
    bulk_file.transaction_to_add = resp["transaction_to_add"]
    bulk_file.transaction_added = resp["transaction_added"]
    bulk_file.errors = resp["errors"]
    bulk_file.save()
    return resp


@task(name="upload_bulk_transaction", queue="low")
def upload_bulk_transaction(bulk_excel_id):
    """To upload bulk transactions."""
    from v2.bulk_templates.serializers.templates import TxnBulkSerializerAsync

    bulk_file = DynamicBulkUpload.objects.get(id=bulk_excel_id)
    data = copy.deepcopy(bulk_file.data)
    ser = TxnBulkSerializerAsync(
        data=data, context={"node": bulk_file.node, "user": bulk_file.creator}
    )
    if not ser.is_valid():
        bulk_file.errors = ser.errors
        bulk_file.save()
        capture_message(
            "Serialization errors in bulk upload.", level="critical"
        )
        raise serializers.ValidationError(ser.errors)
    ser.save()
    return
