"""Exceptions which used in Apps."""
from rest_framework.exceptions import APIException


class BaseAPIException(APIException):
    """Base API Exception to provide option to fail silently."""

    send_to_sentry = True

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        if "send_to_sentry" in kwargs:
            self.send_to_sentry = kwargs.pop("send_to_sentry")
        super(BaseAPIException, self).__init__(*args, **kwargs)


class BadRequest(BaseAPIException):
    """Request method is invalid."""

    status_code = 400
    default_detail = "Request details are invalid."
    default_code = "bad_request"
    send_to_sentry = True


class ParameterMissing(BadRequest):
    """Request method is invalid."""

    status_code = 400
    default_detail = "Missing parameter."
    default_code = "bad_request"
    send_to_sentry = True

    def __init__(self, parameter, *args, **kwargs):
        """To perform function __init__."""
        detail = f"Parameter missing. '{parameter}'."
        super(BaseAPIException, self).__init__(detail, *args, **kwargs)


class UnauthorizedAccess(BaseAPIException):
    """user Authorization failed."""

    status_code = 401
    default_detail = "User is not authorized to access."
    default_code = "unauthorized_access"
    send_to_sentry = False


class AccessForbidden(BaseAPIException):
    """User is not allowed to access."""

    status_code = 403
    default_detail = "User access is forbidden."
    default_code = "access_forbidden"
    send_to_sentry = True


class Conflict(BaseAPIException):
    """Conflict occurred."""

    status_code = 409
    default_detail = "Conflict occurred in the info provided."
    default_code = "conflict"
    send_to_sentry = True


class NotFound(BaseAPIException):
    """NotFound occurred."""

    status_code = 404
    default_detail = "Request object not found."
    default_code = "not_found"
    send_to_sentry = True


class MethodNotAllowed(BaseAPIException):
    """Request method not allowed."""

    status_code = 405
    default_detail = "Method Not Allowed."
    default_code = "method_not_allowed"
    send_to_sentry = True


class PaymentRequired(BaseAPIException):
    """Payment required."""

    status_code = 402
    default_detail = "Does not have sufficient balance"
    default_code = "payment_required"
    send_to_sentry = True
