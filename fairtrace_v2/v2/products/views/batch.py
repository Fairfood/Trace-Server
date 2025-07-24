"""Views related to product in products app."""
from django.db.models import Q
from rest_framework import generics
from rest_framework import views
from rest_framework.viewsets import ReadOnlyModelViewSet
from django.db.models import Sum
from common.library import encode, filter_queryset, success_response, decode
from common.exceptions import BadRequest
from rest_framework import status
from v2.products.constants import UNIT_KG, PRODUCT_TYPE_CARBON
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
        """
        Return a filtered queryset of Batch objects based on request 
        parameters.
        """
        params = self.request.query_params
        is_carbon_product = params.get(
            "is_carbon_product", "false").lower() == "true"
        farmer = params.get("farmer")
        
        if is_carbon_product:
            node = decode(farmer) if farmer else None
            query = Q(node=node, product__type=PRODUCT_TYPE_CARBON)
        else:
            node = self.kwargs.get("node")
            query = Q(
                node=node, current_quantity__gt=0, 
                source_transaction__deleted=False
            )
        return Batch.objects.filter(query).sort_by_query_params(self.request)

    
class BatchSummary(views.APIView):
    """API to list batches of a node with option to filter by product."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    def get(self, request, *args, **kwargs):
        """To perform function get_queryset."""
        query = Q(
            node=self.kwargs["node"], 
            current_quantity__gt=0, 
            source_transaction__deleted=False
        )
        batches = Batch.objects.filter(query)
        batches = BatchFilter(
            data=request.query_params,
            queryset=batches,
            request=request,
        ).qs
        
        selected_batches = batches.values("id","current_quantity")
        selected_batches = map(
            lambda selected_batch :{
                "batch": encode(selected_batch["id"]),
                "quantity": selected_batch["current_quantity"]
                }, 
                selected_batches)
        total_quantity = batches.aggregate(
            Sum('current_quantity'))['current_quantity__sum']
        
        return success_response({
            "total_quantity": total_quantity, 
            "unit": UNIT_KG,
            "selected_batches": selected_batches
            })



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

class BatchArchiveView(generics.CreateAPIView):
    """API to archive transactions."""
    
    queryset = Batch.objects.all()
    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        return super().get_queryset().filter(node=node)

    def post(self, request, *args, **kwargs):
        """Bulk update archived transactions."""
        if not isinstance(request.data, dict):
            raise BadRequest("Invalid data")
        
        selected_items = request.data.get("selected_items", [])
        is_excluded = request.data.get("is_excluded", False)
        restore = request.data.get("restore", False)
        filters = request.data.get("filters", {})
        
        pks = map(decode, selected_items)
        
        if not isinstance(is_excluded, bool):
            raise BadRequest("Invalid data")
        if not isinstance(restore, bool):
            raise BadRequest("Invalid data")
        
        queryset = self.get_queryset().filter(archived=restore)
        queryset = self.filter_queryset_with_data_filters(
            queryset, filters, restore=restore)
        
        if is_excluded:
            queryset = queryset.exclude(pk__in=pks)
        else:
            queryset = queryset.filter(pk__in=pks)
        update_list = []
        for instance in queryset:
            instance.archived = not instance.archived
            update_list.append(instance)
        queryset.model.objects.bulk_update(update_list, ['archived'])
        return success_response(
            {"toggled_items": len(update_list)}, 
            "Archive status toggled", status=status.HTTP_201_CREATED)
    
    def filter_queryset_with_data_filters(self, queryset, filters, restore):
        """Filter queryset with data filters."""
        filters = {k: v for k, v in filters.items() if v}
        if not filters:
            return queryset
        filters["archived"] = restore
        filterset_class = BatchFilter
        return filter_queryset(filterset_class, filters, 
                               queryset, node=self.kwargs["node"])