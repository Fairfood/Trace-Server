"""Views for connection request related urls."""
from common.drf_custom.views import MultiPermissionView
from django.db.models import Q
from rest_framework import generics
from v2.accounts import permissions as user_permissions
from v2.supply_chains import permissions as sc_permissions
from v2.transparency_request.models import ConnectionRequest
from v2.transparency_request.serializers import connection as conn_serializers


class ConnectionRequestView(generics.CreateAPIView):
    """API to create connection requests."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = conn_serializers.ConnectionRequestSerializer


class ConnectionRequestDetails(
    generics.RetrieveUpdateAPIView, MultiPermissionView
):
    """API to list and retrieve connection requests details."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "PATCH": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
    }

    serializer_class = conn_serializers.ConnectionRequestSerializer

    def get_queryset(self):
        """Returns filtered qs."""
        node = self.kwargs["node"]
        query = Q(requestee=node) | Q(requester=node)
        return ConnectionRequest.objects.filter(query)
