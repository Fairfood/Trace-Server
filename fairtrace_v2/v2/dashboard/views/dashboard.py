"""Views related to themes are defined here."""
from rest_framework import generics
from v2.accounts import permissions as user_permissions
from v2.dashboard.serializers.dashboard import StatsSerializer
from v2.supply_chains import permissions as sc_permissions


class StatsView(generics.RetrieveAPIView):
    """API to get statistics of a node to be displayed in the dasbhoard."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = StatsSerializer

    def get_object(self):
        """To perform function get_object."""
        return self.kwargs["node"]

    # def get_queryset(self):
    #     node = self.kwargs['node']
    #     return Node.objects.filter(id=node.id)
