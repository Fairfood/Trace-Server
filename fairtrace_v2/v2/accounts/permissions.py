"""Permissions of the app accounts."""
import pyotp
from common.exceptions import AccessForbidden
from common.exceptions import BadRequest
from common.exceptions import UnauthorizedAccess
from common.library import _decode
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import activate as activate_timezone
from django.utils.translation import activate
from rest_framework import permissions
from v2.transactions import constants as trans_constants

from .constants import USER_TYPE_FAIRFOOD_ADMIN
from .constants import VTOKEN_STATUS_UNUSED
from .models import AccessToken
from .models import ClientVersion
from .models import UserClientVersion
from .models import ValidationToken


class IsAuthenticated(permissions.BasePermission):
    """Check if the user is authenticated.

    Authentication to check if the user access token is valid and fetch
    the user from the token and add it to kwargs.
    """

    def has_permission(self, request, view):
        """To check token."""
        key = request.META.get("HTTP_BEARER")
        user_id = _decode(request.META.get("HTTP_USER_ID"))

        timezone_str = request.META.get("HTTP_TIMEZONE")
        if timezone_str:
            activate_timezone(timezone_str)

        if not key:
            raise BadRequest(
                "Can not find Bearer token in the request header."
            )
        if not user_id:
            raise BadRequest("Can not find User-Id in the request header.")

        try:
            user = AccessToken.objects.get(key=key, user__id=user_id).user
        except Exception:
            raise UnauthorizedAccess(
                "Invalid Bearer token or User-Id, please re-login."
            )
        if user.blocked:
            raise AccessForbidden("user account is blocked, contact admin.")
        request.user = user
        view.kwargs["user"] = user
        version = request.META.get("HTTP_VERSION")
        if not version:
            version = "0.004 or Less"
        client_code = request.META.get(
            "HTTP_CLIENT_CODE", trans_constants.CLIENT_WEB
        )

        self.update_version_details(user, version, client_code)
        return True

    @staticmethod
    def update_version_details(user, version, client_code):
        """Function to create the user client_version using client code.

        client code will be web or app passing through header.
        """
        # default client code will be web.
        client = trans_constants.CLIENT_WEB
        if client_code:
            client = trans_constants.CLIENT_APP

        client_version = ClientVersion.objects.filter(
            name=version, client=client
        ).first()
        if not client_version:
            client_version, created = ClientVersion.objects.get_or_create(
                name=version, client=client
            )
            if created:
                client_version.last_active = timezone.now()
                client_version.save()

        conflict_versions = UserClientVersion.objects.filter(
            user=user, version=client_version
        )
        if conflict_versions.count() > 1:
            conflict_versions.exclude(id=conflict_versions.first().id).delete()
        user_version, created = UserClientVersion.objects.update_or_create(
            user=user, version=client_version
        )
        user_version.last_active = timezone.now()
        user_version.save()
        return True


class IsAuthenticatedWithVerifiedEmail(permissions.BasePermission):
    """Check if the user had verified email.

    Authentication to check if the user has verified his email. Access
    to certain parts of the app will be limited if the user has not
    verified his email.
    """

    def has_permission(self, request, view):
        """To check token."""
        key = request.META.get("HTTP_BEARER")
        user_id = _decode(request.META.get("HTTP_USER_ID"))

        timezone_str = request.META.get("HTTP_TIMEZONE")
        if timezone_str:
            activate_timezone(timezone_str)

        if not key:
            raise BadRequest(
                "Can not find Bearer token in the request header."
            )
        if not user_id:
            raise BadRequest("Can not find User-Id in the request header.")

        try:
            user = AccessToken.objects.get(key=key, user__id=user_id).user
        except Exception:
            raise UnauthorizedAccess(
                "Invalid Bearer token or User-Id, please re-login."
            )

        if user.blocked:
            raise AccessForbidden("User account is blocked, contact admin.")

        if not user.email_verified:
            raise AccessForbidden("User has not verified email.")

        if (
            not user.nodes.exists()
            and not user.type == USER_TYPE_FAIRFOOD_ADMIN
        ):
            raise UnauthorizedAccess("User does not have access to any nodes")
        request.user = user
        view.kwargs["user"] = user
        return True


class IsValidationTokenValid(permissions.BasePermission):
    """Permission to check if the validation token is valid.

    This class will fetch the validation token from the request params
    and add it into kwargs if the token is valid else add None.
    """

    def has_permission(self, request, view):
        """To check validation token."""
        try:
            key = request.data["token"]  # TODO: Move token to header
            pk = request.data["salt"]
        except Exception:
            key = request.query_params["token"]
            pk = request.query_params["salt"]
        if not key:
            raise BadRequest("token can not be empty")
        if not pk:
            raise BadRequest("salt can not be empty")

        try:
            token = ValidationToken.objects.get(id=_decode(pk), key=key)
            if token.status != VTOKEN_STATUS_UNUSED or not token.is_valid:
                raise UnauthorizedAccess("Invalid token.")

        except Exception:
            raise UnauthorizedAccess("Invalid token.")
        view.kwargs["token"] = token
        return True


class HasUserAccess(permissions.BasePermission):
    """This can only be called along with and after IsAuthenticated.

    Checks if signed-in user has access to edit the query user. If both
    of them is the same, true is returned
    """

    def has_permission(self, request, view):
        """To check token."""
        query_user_id = view.kwargs.get("pk", None)
        if not query_user_id or query_user_id == request.user.id:
            view.kwargs["pk"] = request.user.id
            return True
        raise AccessForbidden("Access denied.")


class BaseTOTP(permissions.BasePermission):
    """Base permission class for checking Time-Based One-Time Password (TOTP)
    authentication.

    This base permission class is used for checking TOTP authentication. It
    provides a `has_permission` method that checks the validity of the TOTP
    against the stored secret.

    Attributes:
    - otp_secret: The TOTP secret. This should be overridden in derived
        classes.

    Methods:
    - has_permission(request, view): Checks the TOTP validity.

    Example Usage:
    ```
    class MyTOTP(BaseTOTP):
        # Custom configurations and methods can be added here
        otp_secret = "xxx"
    ```
    """

    otp_secret = None

    def has_permission(self, request, view):
        """To check totp."""
        if settings.ENVIRONMENT == "local":
            return True
        if not self.otp_secret:
            raise UnauthorizedAccess("Failed OTP.", send_to_sentry=False)
        current_otp = request.META.get("HTTP_OTP")
        if not current_otp:
            raise BadRequest("Can not find OTP in the request header.")
        timezone_str = request.META.get("HTTP_TIMEZONE", None)
        language_str = request.META.get("HTTP_LANGUAGE", None)
        if timezone_str:
            activate_timezone(timezone_str)
        if language_str:
            activate(language_str)
        view.kwargs["language"] = language_str
        totp = pyotp.TOTP(self.otp_secret)
        if totp.verify(current_otp, valid_window=1):
            return True
        raise UnauthorizedAccess("Invalid OTP.", send_to_sentry=False)


class ValidTOTP(BaseTOTP):
    """Derived permission class for checking TOTP authentication during
    validation.

    This permission class is used for checking TOTP authentication
    during validation. It inherits from the BaseTOTP class and sets the
    otp_secret to the TOTP token specified in the Django settings.
    """

    otp_secret = settings.TOTP_TOKEN


class LoginTOTP(BaseTOTP):
    """TOTP permission class for login TOTP authentication.

    This permission class checks if the TOTP authentication is valid
    using the login TOTP secret key provided in the settings.
    """

    otp_secret = settings.LOGIN_TOTP_SECRET


class OpenValidTOTP(BaseTOTP):
    """TOTP permission class for login TOTP authentication.

    This permission class checks if the TOTP authentication is valid
    using the open valid TOTP secret key provided in the settings.
    """

    otp_secret = settings.DP_PASS_TOTP_SECRET


class CIValidTOTP(BaseTOTP):
    """TOTP permission class for login TOTP authentication.

    This permission class checks if the TOTP authentication is valid
    using the CI valid TOTP secret key provided in the settings.
    """

    otp_secret = settings.CI_TOTP_SECRET
