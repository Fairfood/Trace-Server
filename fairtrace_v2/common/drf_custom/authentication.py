"""Module to override the default authentication."""
from rest_framework.authentication import (
    TokenAuthentication as RestTokenAuthentication,
)
from v2.accounts.models import AccessToken


class TokenAuthentication(RestTokenAuthentication):
    """Class to override the auth."""

    model = AccessToken
