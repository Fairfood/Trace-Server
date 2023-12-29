"""Views related to themes are defined here."""
from common.exceptions import NotFound
from rest_framework import generics
from v2.accounts import permissions as user_permissions
from v2.dashboard.models import DashboardTheme
from v2.dashboard.serializers.theme import DashboardThemeSerializer
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.models import Node


class FFAdminDashboardThemeView(generics.CreateAPIView):
    """View to add Dashboard Theme."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = DashboardThemeSerializer


class FFAdminDashboardThemeDetailsView(generics.RetrieveUpdateAPIView):
    """This class will retrieve and updates Dashboard Theme details."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    queryset = DashboardTheme.objects.all()
    serializer_class = DashboardThemeSerializer


class NodeDashboardThemeView(generics.RetrieveUpdateAPIView):
    """API to get Theme."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = DashboardThemeSerializer

    def get_object(self):
        """To perform function get_object."""
        node = self.kwargs["node"]
        try:
            if node.features.dashboard_theming:
                return node.dashboard_theme
        except Node.features.RelatedObjectDoesNotExist:
            pass
        except Node.dashboard_theme.RelatedObjectDoesNotExist:
            pass
        raise NotFound
