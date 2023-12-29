"""Views related to product in products app."""
from common.drf_custom.views import MultiPermissionView
from django.db.models import Q
from rest_framework import generics
from v2.accounts import permissions as user_permissions
from v2.products.constants import PRODUCT_TYPE_GLOBAL
from v2.products.constants import PRODUCT_TYPE_LOCAL
from v2.products.filters import ProductFilter
from v2.products.models import Product
from v2.products.serializers import product as product_serializers
from v2.supply_chains import permissions as sc_permissions


class ProductView(generics.ListCreateAPIView, MultiPermissionView):
    """API to list and create Products based on a supplychain."""

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

    serializer_class = product_serializers.ProductSerializer
    filterset_class = ProductFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        query = Q(type=PRODUCT_TYPE_GLOBAL)
        query |= Q(type=PRODUCT_TYPE_LOCAL, owners=self.kwargs["node"])
        # node = self.kwargs['node']
        # my_products = self.request.query_params.get('my_products', None)
        # if my_products:
        #     return node.get_products()
        return (
            Product.objects.filter(query)
            .order_by("name", "id")
            .distinct("name", "id")
        )


class BulkCreateProduct(generics.CreateAPIView):
    """Class to handle BulkCreateProduct and functions."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = product_serializers.BulkCreateProduct


class ProductListView(generics.ListAPIView):
    """API to get Products based on a supplychain for verification list."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = product_serializers.ProductSerializer
    filterset_class = ProductFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        return (
            Product.objects.filter(batches__claims__verifier=node)
            .order_by("name", "id")
            .distinct("name", "id")
        )
