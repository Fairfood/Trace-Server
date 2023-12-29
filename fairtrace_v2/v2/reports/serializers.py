from operator import methodcaller

from common.drf_custom import serializers
from common.library import decode
from common.library import filter_queryset
from django.db import transaction as db_transaction
from django.db.models import Q
from v2.products.filters import BatchFilter
from v2.products.models import Batch
from v2.projects.models import Payment
from v2.reports.constants import ADMIN_COMPANY
from v2.reports.constants import ADMIN_EXTERNAL_TRANSACTION
from v2.reports.constants import ADMIN_FARMER
from v2.reports.constants import COMPANY
from v2.reports.constants import CONNECTIONS
from v2.reports.constants import EXTERNAL_TRANSACTION
from v2.reports.constants import FARMER
from v2.reports.constants import INTERNAL_TRANSACTION
from v2.reports.constants import PAYMENTS
from v2.reports.constants import STOCK
from v2.reports.generators import generate_file
from v2.reports.models import Export
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.filters import CompanyFilter
from v2.supply_chains.filters import FarmerFilter
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import SupplyChain
from v2.transactions.filters import ExternalTransactionFilter
from v2.transactions.filters import InternalTransactionFilter
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import InternalTransaction


class ExportSerializer(serializers.IdencodeModelSerializer):
    """Export serializer to create, list the export entries."""

    EXPORT_TYPE_MAP = {
        STOCK: "get_stoke_qs",
        INTERNAL_TRANSACTION: "get_internal_transaction_qs",
        EXTERNAL_TRANSACTION: "get_external_transaction_qs",
        CONNECTIONS: "get_connection_qs",
        FARMER: "get_farmer_qs",
        COMPANY: "get_company_qs",
        ADMIN_COMPANY: "get_admin_company_qs",
        ADMIN_FARMER: "get_admin_farmer_qs",
        ADMIN_EXTERNAL_TRANSACTION: "get_admin_transaction_qs",
        PAYMENTS: "get_payment_qs",
    }

    class Meta:
        model = Export
        fields = (
            "id",
            "export_type",
            "file",
            "file_name",
            "status",
            "filters",
            "etc",
            "node",
            "file_type",
            "creator",
            "created_on",
            "updated_on",
        )

    @db_transaction.atomic()
    def create(self, validated_data):
        """Overrides create to trigger file."""
        instance = super().create(validated_data)
        qs = self.get_queryset(instance.id)
        instance.file_name = instance.initial_file_name
        instance.rows = qs.count()
        instance.etc = round(instance.initial_etc * instance.rows)
        instance.save(update_fields=["etc", "file_name", "rows"])
        db_transaction.on_commit(lambda: self.start_task(instance, qs))
        return instance

    @staticmethod
    def start_task(instance, qs):
        """Create task and register that task with the current instance."""
        # noinspection PyProtectedMember
        tsk = generate_file.apply_async(
            (
                instance.id,
                list(qs.values_list("id", flat=True)),
                qs.model.__name__,
                qs.model._meta.app_label,
                instance.file_name,
            )
        )
        instance.task_id = tsk.task_id
        instance.save(update_fields=["task_id"])

    def get_queryset(self, instance_id):
        """Get filtered queryset according to the export_type."""
        # Need to get instance to avoid JsonDict issue
        instance = self.Meta.model.objects.get(pk=instance_id)
        method = methodcaller(
            self.EXPORT_TYPE_MAP[instance.export_type], instance
        )
        return method(self)

    @staticmethod
    def get_stoke_qs(instance):
        """Get filtered queryset."""
        qs = Batch.objects.filter(node=instance.node, current_quantity__gt=0)
        filterset_class = BatchFilter
        return filter_queryset(
            filterset_class, instance.filters, qs, node=instance.node
        )

    @staticmethod
    def get_internal_transaction_qs(instance):
        """Get filtered queryset."""
        qs = InternalTransaction.objects.filter(node=instance.node)
        filterset_class = InternalTransactionFilter
        return filter_queryset(
            filterset_class, instance.filters, qs, node=instance.node
        )

    @staticmethod
    def get_external_transaction_qs(instance):
        """Get filtered queryset."""
        qs = ExternalTransaction.objects.filter(
            Q(source=instance.node) | Q(destination=instance.node)
        )
        filterset_class = ExternalTransactionFilter
        return filter_queryset(
            filterset_class, instance.filters, qs, node=instance.node
        )

    @staticmethod
    def get_connection_qs(instance):
        """Get filtered queryset."""
        filters = {}
        if "supply_chain" in instance.filters:
            filters["supply_chain"] = SupplyChain.objects.get(
                pk=decode(instance.filters["supply_chain"])
            )
        suppliers = instance.node.get_supplier_chain(
            include_self=True, **filters
        )[0]
        buyers = instance.node.get_buyer_chain(**filters)[0]
        return suppliers | buyers

    def get_farmer_qs(self, instance):
        """Get filtered queryset."""
        qs = self.get_connection_qs(instance)
        return qs.filter(type=NODE_TYPE_FARM)

    def get_company_qs(self, instance):
        """Get filtered queryset."""
        qs = self.get_connection_qs(instance)
        return qs.filter(type=NODE_TYPE_COMPANY)

    @staticmethod
    def get_admin_company_qs(instance):
        """Get filtered queryset for admin_company."""
        qs = Company.objects.all()
        filterset_class = CompanyFilter
        return filter_queryset(filterset_class, instance.filters, qs)

    @staticmethod
    def get_admin_farmer_qs(instance):
        """Get filtered queryset for admin_farmer."""
        qs = Farmer.objects.all()
        filterset_class = FarmerFilter
        return filter_queryset(filterset_class, instance.filters, qs)

    @staticmethod
    def get_admin_transaction_qs(instance):
        """Get filtered queryset for admin_transaction."""
        qs = ExternalTransaction.objects.all()
        filterset_class = ExternalTransactionFilter
        return filter_queryset(filterset_class, instance.filters, qs)

    @staticmethod
    def get_payment_qs(instance):
        """Get filtered queryset for payments."""
        qs = Payment.objects.all()
        return qs.filter_by_data(instance.filters)
