"""General API returning static data."""
from common.country_data import COUNTRIES
from common.library import _success_response
from rest_framework.views import APIView
from v2.accounts import permissions as user_permissions


class CountryData(APIView):
    """Class to handle CountryData and functions."""

    permission_classes = (user_permissions.IsAuthenticated,)

    @staticmethod
    def get(request, user, *args, **kwargs):
        """Returns the country data."""
        return _success_response(COUNTRIES)
