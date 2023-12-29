"""Permissions of the blockchain operations."""
from rest_framework import permissions
from rest_framework.exceptions import APIException

from .library import decode
from .models.callback_auth import CallBackToken


class UnauthorizedAccess(APIException):
    """user Authorization failed."""

    status_code = 401
    default_detail = "User is not authorized to access."
    default_code = "unauthorized_access"


class ValidCallBackToken(permissions.BasePermission):
    """Check if the CallBackToken is valid."""

    def has_permission(self, request, view):
        """To check callback token token."""
        try:
            token = request.query_params.get("token", "")
            pk = decode(request.query_params.get("salt", ""))

            assert token, "Token can not be empty"
            assert pk, "Salt can not be empty"

            try:
                cb_token = CallBackToken.objects.get(id=pk, key=token)
            except Exception as e:
                raise UnauthorizedAccess(f"Could not find Token. {e}")
            if not cb_token.is_valid:
                raise UnauthorizedAccess("Invalid token.")
            view.kwargs["token"] = cb_token
            return True
        except Exception as e:
            raise e
