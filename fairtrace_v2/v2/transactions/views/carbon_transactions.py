"""Views related to carbon transactions in transactions app."""
from django.db.models import Q
from rest_framework.generics import ListCreateAPIView, ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from common.drf_custom.views import MultiPermissionView
from common.exceptions import BadRequest
from common.library import get_node_from_request
from v2.accounts import permissions as user_permissions
from v2.supply_chains import permissions as sc_permissions
from v2.products.constants import PRODUCT_TYPE_CARBON
from v2.transactions.filters import ExternalTransactionFilter
from v2.transactions.filters import InternalTransactionFilter
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import InternalTransaction
from v2.transactions.serializers.external import (
    ExternalTransactionListSerializer,
)
from v2.transactions.serializers.carbon import (
    CarbonExternalTransactionSerializer, CarbonTransactionSerializer, 
    CarbonInternalTransactionSerializer
)
from v2.transactions.serializers.internal import (
    InternalTransactionListSerializer
)


class CarbonExternalTransactionView(ListCreateAPIView, MultiPermissionView):
    """View to list and create carbon external transaction."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "POST": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
    }

    filterset_class = ExternalTransactionFilter
    serializer_class = CarbonExternalTransactionSerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        node = get_node_from_request(self.request)
        if not node:
            raise BadRequest("Invalid Node", send_to_sentry=False)
        query = Q(source=node) | Q(destination=node)
        query = (Q(source=node) | Q(destination=node)) & Q(deleted=False)
        transactions = ExternalTransaction.objects.filter(query)
        return transactions.sort_by_query_params(self.request).distinct()

    def get_serializer_class(self):
        """Fetch corresponding serializer class."""
        if self.request.method == "POST":
            return CarbonExternalTransactionSerializer
        return ExternalTransactionListSerializer


class CarbonInternalTransactionView(ListCreateAPIView, MultiPermissionView):
    """View to list and create carbon internal transactions."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "POST": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
    }
    filterset_class = InternalTransactionFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        node = get_node_from_request(self.request)
        if not node:
            raise BadRequest("Invalid Node", send_to_sentry=False)
        transactions = InternalTransaction.objects.filter(
            node=node, deleted=False
        )
        return transactions.sort_by_query_params(self.request)

    def get_serializer_class(self):
        """Fetch corresponding serializer class."""
        if self.request.method == "POST":
            return CarbonInternalTransactionSerializer
        return InternalTransactionListSerializer


class CarbonTransactionsView(ListAPIView):
    """View to list carbon internal and external transactions."""

    permission_classes = [
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    ]
    serializer_class = CarbonTransactionSerializer

    def get(self, request, *args, **kwargs):
        node = get_node_from_request(request)
        if not node:
            raise BadRequest("Invalid Node", send_to_sentry=False)

        external_trans = self._get_external_transactions(node)
        internal_trans = self._get_internal_transactions(node)

        # Combine both external and internal transactions
        all_trans = list(external_trans) + list(internal_trans)

        #apply search
        all_trans = self._search(
            all_trans, 
            fields=[
                'number',
                'source.farmer.first_name',
                'source.farmer.last_name',
                'source.company.name',
                'destination.farmer.first_name',
                'destination.farmer.last_name',
                'destination.company.name',
                'node.farmer.first_name',
                'node.farmer.last_name',
                'node.company.name',
            ]
        )

        # Apply pagination
        paginator = LimitOffsetPagination()
        paginated_data = paginator.paginate_queryset(all_trans, request)

        # Serialize the data
        serializer = CarbonTransactionSerializer(
            paginated_data, many=True, context={'request': request}
        )

        # Return the paginated response
        return paginator.get_paginated_response(serializer.data)

    def _get_external_transactions(self, node):
        """
        Helper function to get external transactions for a given node.
        Returns a queryset of external transactions.
        """
        carbon_product_query = (
            Q(source_batches__product__type=PRODUCT_TYPE_CARBON) |
            Q(result_batches__product__type=PRODUCT_TYPE_CARBON)
        )
        ext_query = (
            (Q(source=node) | Q(destination=node)) & 
            Q(deleted=False) & carbon_product_query
        )
        return ExternalTransaction.objects.filter(ext_query).select_related(
            'source', 'destination').prefetch_related('parents')

    def _get_internal_transactions(self, node):
        """
        Helper function to get internal transactions for a given node.
        Returns a queryset of internal transactions.
        """
        carbon_product_query = (
            Q(source_batches__product__type=PRODUCT_TYPE_CARBON) |
            Q(result_batches__product__type=PRODUCT_TYPE_CARBON)
        )
        internal_query = Q(node=node) & carbon_product_query
        return InternalTransaction.objects.filter(internal_query).select_related(
            'node').prefetch_related('parents')
    
    def _get_nested_attr(self, obj, attr_path):
        """
        Split the attribute path by '.' (dot) to handle nested fields
        """
        attrs = attr_path.split('.')
        for attr in attrs:
            if hasattr(obj, attr):
                obj = getattr(obj, attr, None)
        return obj

    def _search(self, all_trans, fields=None):
        """Search across multiple (including nested) fields"""
        search_query = self.request.query_params.get('search')
        if not search_query:
            return all_trans

        search_query = search_query.strip().lower()

        def matches_search(trans):
            """
            Iterate through each field and check if the value matches the 
            search query
            """
            for field in fields:
                value = self._get_nested_attr(trans, field)
                if value and search_query in str(value).lower():
                    return True
            return False

        return [trans for trans in all_trans if matches_search(trans)]

