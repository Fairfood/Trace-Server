"""Views related to product in products app."""
from django.db.models import Q
from rest_framework import generics
from rest_framework.viewsets import ReadOnlyModelViewSet
from v2.accounts import permissions as user_permissions
from v2.products.filters import BatchFarmerMappingFilter
from v2.products.filters import BatchFilter
from v2.products.models import Batch
from v2.products.models import BatchFarmerMapping
from v2.products.serializers import batch as batch_serializers
from v2.products.serializers.batch import BatchFarmerMappingSerializer
from v2.supply_chains import permissions as sc_permissions


class BatchList(generics.ListAPIView):
    """API to list batches of a node with option to filter by product."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = batch_serializers.BatchSerializer
    filterset_class = BatchFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        query = Q(node=self.kwargs["node"], current_quantity__gt=0)
        batches = Batch.objects.filter(query)
        return batches.sort_by_query_params(self.request)


class BatchDetails(generics.RetrieveUpdateAPIView):
    """API to get batch details."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = batch_serializers.BatchDetailSerializer

    queryset = Batch.objects.all()


# class BatchCommentView(generics.CreateAPIView):
#     """ API to list batches of a node with option to filter by product """
#
#     permission_classes = (
#         user_permissions.IsAuthenticatedWithVerifiedEmail,
#         sc_permissions.HasNodeWriteAccess)
#
#     serializer_class = batch_serializers.BatchCommentSerializer


class BatchFarmerMappingViewSet(ReadOnlyModelViewSet):
    """Viewset for retrieving batch-farmer mappings.

    This viewset provides read-only endpoints for retrieving batch-
    farmer mappings. It inherits from the ReadOnlyModelViewSet class,
    which includes default implementation for retrieving and displaying
    model instances.
    """

    queryset = BatchFarmerMapping.objects.all()
    serializer_class = BatchFarmerMappingSerializer
    filterset_class = BatchFarmerMappingFilter

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )
