from common.library import success_response
from django.db.models import Sum
from rest_framework import viewsets
from v2.accounts.permissions import IsAuthenticated
from v2.products.models import Product
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Node
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.permissions import IsFairfoodAdmin
from v2.transactions.filters import ExternalTransactionFilter
from v2.transactions.models import ExternalTransaction
from v2.transactions.serializers.admin_dashboard_v3 import (
    AdminExternalTransactionModelSerializer,
)


class AdminExternalTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """API to list all External Transactions in the system."""

    permission_classes = (IsAuthenticated, IsFairfoodAdmin)
    queryset = ExternalTransaction.objects.filter(deleted=False).exclude_test()
    filterset_class = ExternalTransactionFilter
    serializer_class = AdminExternalTransactionModelSerializer

    def get_queryset(self):
        """Adding extra qs functions."""
        return super().get_queryset().sort_by_query_params(self.request)


class AdminExternalTransactionCountViewSet(viewsets.ViewSet):
    """API to count external transactions against each joined date available.
    For showing as a graph in Admin Dashboard.

    Returns data in the following format.

    *   [
            {
                "grouped_by": "2020-01-01T00:00:00+05:30",
                "truncated_by": "month",
                "count": 19,
            },
            {
                "grouped_by": "2020-02-01T00:00:00+05:30",
                "truncated_by": "month",
                "count": 39,
            }
     ]
    """

    permission_classes = (IsAuthenticated, IsFairfoodAdmin)
    queryset = ExternalTransaction.objects.sourced_from_farmers()

    def list(self, request, *args, **kwargs):
        """Returns the grouped transactions with count."""
        queryset = self.queryset.filter_queryset(request).exclude_test()
        trunc_type = request.query_params.get("trunc_type", None)
        if not trunc_type:
            data = queryset.group_count_with_date()
        else:
            data = queryset.group_count_with_date(trunc_type)
        return success_response(data)


class AdminExternalTransactionQuantityViewSet(viewsets.ViewSet):
    """API to display  total quantity  of external transactions against each
    date available. For showing as a graph in Admin Dashboard.

    Returns data in the following format.

    *   [
             {
                "truncated_by": "month",
                "grouped_by": "2022-12-01T00:00:00+05:30",
                "total_quantity": 67.0
            },
            {
                "truncated_by": "month",
                "grouped_by": "2023-12-01T00:00:00+05:30",
                "total_quantity": 65.0
            }
     ]
    """

    permission_classes = (IsAuthenticated, IsFairfoodAdmin)
    queryset = ExternalTransaction.objects.all()

    def list(self, request, *args, **kwargs):
        """Returns the grouped transactions with Quantity."""
        queryset = self.queryset.filter_queryset(request).exclude_test()
        trunc_type = request.query_params.get("trunc_type", None)
        if not trunc_type:
            data = queryset.group_quantity_with_created_on()
        else:
            data = queryset.group_quantity_with_created_on(trunc_type)
        return success_response(data)


class AdminStatisticsViewSet(viewsets.ViewSet):
    """API to display overall statistics data in admin-dashboard.

    Returns data in the following format.

    *   {
            "farmers": 31280,
            "companies": 3500,
            "active_companies": 2218,
            "pending_companies": 1282,
            "actors": 34780,
            "transactions": 7386,
            "supply_chains": 73,
            "products": 514,
            "farmer_transaction_quantity": 417382206680.09,
            "farmer_transactions": 6804
        }
    """

    permission_classes = (IsAuthenticated, IsFairfoodAdmin)
    queryset = ExternalTransaction.objects.all()

    def list(self, request, *args, **kwargs):
        """for list api."""
        data = self._get_data()

        # Get farmer transactions from total transaction.
        farmer_transaction = (
            ExternalTransaction.objects.filter_queryset(request)
            .exclude_test()
            .sourced_from_farmers()
        )
        farmer_quantity = farmer_transaction.aggregate(
            quantity=Sum("_source_quantity")
        )

        # Get Company transactions with farmer transactions
        company_transactions = (
            ExternalTransaction.objects.filter_queryset(request)
            .exclude_test()
            .sourced_from_company()
        )

        # Append extra details with data.
        data["farmer_transaction_quantity"] = farmer_quantity["quantity"]
        data["farmer_transactions"] = farmer_transaction.count()
        data["company_transactions"] = company_transactions.count()
        return success_response(data)

    def _get_data(self):
        """To create a data set with request."""
        request = self.request
        return {
            "farmers": (
                Farmer.objects.filter_queryset(request).exclude_test().count()
            ),
            "companies": (
                Company.objects.filter_queryset(request).exclude_test().count()
            ),
            "active_companies": (
                Company.objects.filter_queryset(request)
                .exclude_test()
                .only_active()
                .count()
            ),
            "pending_companies": (
                Company.objects.filter_queryset(request)
                .exclude_test()
                .only_pending()
                .count()
            ),
            "actors": (
                Node.objects.filter_queryset(request).exclude_test().count()
            ),
            "transactions": (
                ExternalTransaction.objects.filter_queryset(request)
                .exclude_test()
                .count()
            ),
            "supply_chains": (
                NodeSupplyChain.objects.exclude_test()
                .distinct("supply_chain")
                .order_by()
                .count()
            ),
            "products": Product.objects.filter_queryset(request).count(),
        }
