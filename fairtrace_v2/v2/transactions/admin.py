from common.admin import BaseAdmin
from django.contrib import admin
from v2.products.models import Batch
from v2.projects.models import Payment
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import InternalTransaction
from v2.transactions.models import SourceBatch
from v2.transactions.models import Transaction


class SourceBatchInline(admin.TabularInline):
    """In-line view function for SourceBatch."""

    readonly_fields = (
        "creator",
        "updater",
        "batch",
        "block_chain_request",
        "submit_message_request",
    )

    model = SourceBatch
    extra = 0


class PaymentInline(admin.TabularInline):
    """In-line view function for SourceBatch."""

    readonly_fields = (
        "idencode",
        "premium",
        "amount",
        "creator",
        "updater",
        "source",
        "destination",
        "payment_type",
        "invoice_number"
    )

    model = Payment
    extra = 0


class BatchInline(admin.TabularInline):
    """In-line view function for SourceBatch."""

    readonly_fields = (
        "idencode",
        "number",
        "initial_quantity",
        "current_quantity",
        "unit",
        "verified_percentage",
        "node",
        "product",
        "block_chain_request",
        "submit_message_request",
        "node_wallet",
        "creator",
        "updater",
    )

    model = Batch
    extra = 0


class TransactionAdmin(BaseAdmin):
    """Admin for Base transaction."""

    list_display = ("idencode", "status", "transaction_type")
    inlines = [SourceBatchInline, BatchInline]
    readonly_fields = (
        "parents",
        "source_batches",
        "creator",
        "updater",
        "card",
    )
    search_fields = ("number",)


class ExternalTransactionAdmin(BaseAdmin):
    """Admin for External transaction."""

    list_display = (
        "idencode",
        "source",
        "destination",
        "status",
        "type",
        "created_on",
    )
    inlines = [SourceBatchInline, BatchInline, PaymentInline]
    list_select_related = (
        "source",
        "source__farmer",
        "source__company",
        "destination",
        "destination__farmer",
        "destination__company",
    )
    readonly_fields = (
        "source",
        "destination",
        "source_wallet",
        "destination_wallet",
        "parents",
        "block_chain_request",
        "number",
        "date",
        "creator",
        "updater",
        "transaction_type",
        "block_chain_request",
        "submit_message_request",
        "created_on",
        "updated_on",
        "card",
    )
    search_fields = [
        "source__farmer__first_name",
        "source__farmer__last_name",
        "source__company__name",
        "destination__farmer__first_name",
        "destination__farmer__last_name",
        "destination__company__name",
        "creator__first_name",
        "creator__last_name",
    ]
    ordering = ("-id",)
    # list_filter = ('source', 'destination', 'creator')


class InternalTransactionAdmin(BaseAdmin):
    """Admin for Internal transactions."""

    list_display = ("idencode", "node", "type", "mode")
    inlines = [SourceBatchInline, BatchInline]
    readonly_fields = (
        "parents",
        "node",
        "creator",
        "updater",
        "submit_message_request",
        "node_wallet",
        "card",
    )
    list_select_related = (
        "node",
        "node__farmer",
        "node__company",
    )
    search_fields = [
        "node__farmer__first_name",
        "node__farmer__last_name",
        "node__company__name",
        "creator__first_name",
        "creator__last_name",
    ]
    # list_filter = ('node', 'creator')


admin.site.register(Transaction, TransactionAdmin)
admin.site.register(ExternalTransaction, ExternalTransactionAdmin)
admin.site.register(InternalTransaction, InternalTransactionAdmin)
