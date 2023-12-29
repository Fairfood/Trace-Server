"""Views related to project configurations are defined here."""
from common.library import _success_response
from rest_framework.views import APIView
from v2.accounts import permissions as user_permissions
from v2.dashboard.serializers.configuration import ConfigurationsSerializer


class ConfigurationsView(APIView):
    """Class to handle ConfigurationsView and functions."""

    permission_classes = (user_permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        """To perform function get."""
        config = ConfigurationsSerializer()
        return _success_response(config.to_representation())
