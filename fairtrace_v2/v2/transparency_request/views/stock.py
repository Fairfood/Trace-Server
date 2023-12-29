"""Views for transparency_request related urls."""
from common import library as comm_lib
from common.drf_custom.views import MultiPermissionView
from common.exceptions import BadRequest
from django.db.models import Q
from rest_framework import generics
from v2.accounts import permissions as user_permissions
from v2.supply_chains import permissions as sc_permissions
from v2.transparency_request.filters import StockRequestFilter
from v2.transparency_request.models import StockRequest
from v2.transparency_request.serializers import stock as stock_serializers


class StockRequestListCreateView(
    generics.ListCreateAPIView, MultiPermissionView
):
    """List and create API for transparency request."""

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

    serializer_class = stock_serializers.StockRequestSerializer

    filterset_class = StockRequestFilter

    def get_queryset(self):
        """Returns filtered qs."""
        node = self.kwargs["node"]
        query = Q(requester=node) | Q(requestee=node)
        query &= Q(deleted=False)
        return StockRequest.objects.filter(query)


class StockRequestRetrieveDestroyView(
    generics.RetrieveUpdateDestroyAPIView, MultiPermissionView
):
    """Get details, update and delete API for transparency request."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "POST": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
        "PATCH": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
        "DELETE": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
    }

    serializer_class = stock_serializers.StockRequestSerializer

    def get_queryset(self):
        """Returns filtered qs."""
        node = self.kwargs["node"]
        query = Q(requester=node) | Q(requestee=node)
        query &= Q(deleted=False)
        return StockRequest.objects.filter(query)

    def destroy(self, request, *args, **kwargs):
        """To delete instance."""
        node = self.kwargs["node"]
        stock_request = self.get_object()
        if stock_request.requester != node:
            raise BadRequest(
                "Only the sender of the Transparency request can delete it."
            )
        if not stock_request.is_modifiable():
            raise BadRequest(
                "Transparency request cannot be removed. It might be"
                " completed."
            )
        stock_request.remove()
        return comm_lib._success_response(
            {}, "Transparency request removed", 200
        )


# class StockRequestRejectView(APIView):
#     """
#     Reject API for Stock request
#     """
#     permission_classes = (
#         user_permissions.IsAuthenticatedWithVerifiedEmail,
#         sc_permissions.HasNodeWriteAccess)
#
#     def post(self, request, *args, **kwargs):
#         node = kwargs['node']
#         response = request.data.get('note', "")
#         stock_request = StockRequest.objects.get(id=kwargs['pk'])
#         if stock_request.requestee != node:
#             raise BadRequest("Only the receiver of the Transparency request
#             can reject it.")
#         if not stock_request.is_modifiable():
#             raise BadRequest("Transparency request cannot be rejected.
#             It might be completed.")
#         stock_request.reject(response)
#         return comm_lib._success_response(
#             {}, 'Transparency request rejected', 200
#         )


class StockRequestVerificationView(generics.CreateAPIView):
    """View to verify if a list of batches can be used for a transaction.

    It check if the required claims are approved in the batch
    """

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = stock_serializers.StockRequestVerificationSerializer
