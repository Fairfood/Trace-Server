"""Views related to activities."""
from common.library import decode
from rest_framework import generics
from v2.accounts import permissions as user_permissions
from v2.activity.filters import ActivityFilter
from v2.activity.models import Activity
from v2.activity.serializers.activity import NodeActivitySerializer
from v2.activity.serializers.activity import UserActivitySerializer
from v2.supply_chains import permissions as sc_permissions


class NodeActivity(generics.ListAPIView):
    """API to get batch details."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = NodeActivitySerializer

    filterset_class = ActivityFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.request.query_params.get("node")
        if not node:
            node = self.kwargs["node"].idencode
        return Activity.objects.filter(node_id=decode(node))


class UserActivity(generics.ListAPIView):
    """API to get batch details."""

    permission_classes = (user_permissions.IsAuthenticatedWithVerifiedEmail,)

    serializer_class = UserActivitySerializer

    filterset_class = ActivityFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        user = self.kwargs["user"]
        return Activity.objects.filter(user=user)
