"""Views related to user account and tokens."""
import requests
from common import library as comm_lib
from common.exceptions import BadRequest
from common.library import decode, success_response
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction as db_transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import generics, mixins, views
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from v2.accounts import permissions as user_permissions
from v2.accounts.constants import (GOOGLE_ACCESS_TOKEN_OBTAIN_URL,
                                   GOOGLE_USER_INFO_URL, VTOKEN_STATUS_UNUSED,
                                   VTOKEN_TYPE_CHANGE_EMAIL, VTOKEN_TYPE_OTP,
                                   VTOKEN_TYPE_RESET_PASS,
                                   VTOKEN_TYPE_VERIFY_EMAIL)
from v2.accounts.models import FairfoodUser, ValidationToken
from v2.accounts.permissions import LoginTOTP
from v2.accounts.serializers import auth as auth_serializers
from v2.accounts.serializers import user as user_serializers
from v2.accounts.serializers.user import InviteeUserSerializer
from v2.supply_chains.models import NodeMember

USER_MODEL = get_user_model()


# accounts/validate/username/
class ValidateUsername(generics.RetrieveAPIView):
    """View to check username availability."""

    permission_classes = (LoginTOTP,)
    serializer_class = auth_serializers.ValidateUsernameSerializer

    @staticmethod
    def post(request, *args, **kwargs):  # TODO: remove post here
        """Function to get username availability.

        Request Params:
            username(str): user name.
            type(int): type of user account.
        Response:
            Response. with,
            success(bool): success status of the response.
            message(str): Status description message.
            code(int): status code.
            data(dict): data info.
                valid(bool): true or false value.
                available(bool): true or false value.
                message(str): validation message
        """
        serializer = auth_serializers.ValidateUsernameSerializer(
            data=request.data
        )
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)

        return comm_lib._success_response(serializer.data)


# accounts/validate/password/
class ValidatePassword(generics.RetrieveAPIView):
    """View to check password validity."""

    permission_classes = (LoginTOTP,)

    @staticmethod
    def post(request, *args, **kwargs):  # TODO: remove post
        """Function to get username availability.

        Request Params:
            password(str): password.
            type(int): type of user account.
        Response:
            Response. with,
            success(bool): success status of the response.
            message(str): Status description message.
            code(int): status code.
            data(dict): data info.
                valid(bool): true or false value.
                message(str): validation message
        """
        serializer = auth_serializers.ValidatePasswordSerializer(
            data=request.data
        )
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)

        return comm_lib._success_response(serializer.data)


# accounts/validator/
class ManageValidator(APIView):
    """View to perform validation token management."""

    # TODO: Move logic to serializer
    permission_classes = (LoginTOTP,)
    http_method_names = ["get", "post"]

    @staticmethod
    def fetch_token_salt(request):
        """To perform function tch_token_salt."""
        key = request.data.get("token")
        pk = request.data.get("salt")
        key = key or request.query_params.get("token")
        pk = pk or request.query_params.get("salt")
        if not key:
            raise BadRequest("token can not be empty")
        if not pk:
            raise BadRequest("salt can not be empty")
        return key, pk

    @staticmethod
    def check_token_validity(key, pk):
        """To perform function check_token_validity."""
        try:
            token = ValidationToken.objects.get(
                id=comm_lib._decode(pk), key=key, status=VTOKEN_STATUS_UNUSED
            )

            if not token.is_valid:
                token = None
        except Exception:
            token = None
        return token

    def validate(self, request, token=None):
        """Function to execute validation token.

        Request Params:
            Following params are mandatory in the request body,
            salt(char): salt value.
            token(char): 90 digit reset token.

            Following params are supplied from the permissions,
            token(obj): validation token object.
        Response:
            Response:
            Response. with,
            success(bool): success status of the response.
            message(str): Status description message.
            code(int): status code.
            data(dict): data info.
                valid(bool): true or false value.
        """

        key, pk = self.fetch_token_salt(request)
        token = self.check_token_validity(key, pk)
        resp = {}

        if token:
            user = token.user
            user.email_verified = True
            user.save()
            if token.user.password and token.type != VTOKEN_TYPE_RESET_PASS:
                resp["set_password"] = False
            else:
                resp["set_password"] = True
            if token.type == VTOKEN_TYPE_VERIFY_EMAIL:
                token.mark_as_used()
                resp["valid"] = True
                resp["message"] = "Verification completed."
            elif token.type == VTOKEN_TYPE_CHANGE_EMAIL:
                token.mark_as_used()
                success = token.user.confirm_updated_email()
                if success:
                    resp["valid"] = True
                    resp["message"] = "Verification completed. Email changed"
            else:
                resp["valid"] = True
                resp["message"] = "Token is valid and active."
        else:
            resp["set_password"] = False
            resp["valid"] = False
            resp["message"] = "Token is invalid/expired."
        return comm_lib._success_response(resp)

    def get(self, request, token=None, *args, **kwargs):
        """GET request end point."""
        return self.validate(request, token)

    def post(self, request, token=None, *args, **kwargs):
        """POST request end point."""
        return self.validate(request, token)


# accounts/shop/signup/
class Signup(generics.CreateAPIView):
    """View to Sign up user."""

    permission_classes = (LoginTOTP,)
    serializer_class = user_serializers.UserSerializer


# accounts/device/
class CreateUserDevice(generics.CreateAPIView):
    """User device create."""

    serializer_class = user_serializers.UserDeviceSerializer
    permission_classes = (user_permissions.IsAuthenticated,)

    def get_serializer_context(self):
        """Overriding method to pass user."""
        # Check for mutable flag present for request data.
        if hasattr(self.request.data, "_mutable"):
            self.request.data._mutable = True
        self.request.data["user"] = self.kwargs["user"].id
        self.request.data["creator"] = self.kwargs["user"].id
        if self.request.data._mutable:
            self.request.data._mutable = False
        return {"request": self.request}


# accounts/login
class Login(generics.CreateAPIView):
    """Login view."""

    permission_classes = (LoginTOTP,)
    serializer_class = auth_serializers.LoginSerializer


class EmailLogin(APIView):
    """Login with email view."""

    permission_classes = (LoginTOTP,)

    def post(self, request, *args, **kwarg):
        """Sent login code to the email if user exists."""

        # get email from request.
        email = request.data.get("email", None)
        if not email:
            raise ValidationError("email is required.")

        # find user
        try:
            user = FairfoodUser.objects.get(username=email)
        except FairfoodUser.DoesNotExist:
            raise ValidationError("Invalid email.")

        # send code to user email.
        user.sent_otp()
        return success_response({"message": "Done"})


class EmailLoginCode(APIView):
    """Login with email view."""

    permission_classes = (LoginTOTP,)

    def post(self, request, *args, **kwarg):
        """Sent login code to the email if user exists."""

        # get email and code from request.
        email = request.data.get("email", None)
        code = request.data.get("code", None)
        if not email or not code:
            raise ValidationError("email and code is required.")

        # find user
        try:
            user = FairfoodUser.objects.get(username=email)
        except FairfoodUser.DoesNotExist:
            raise ValidationError(detail="Invalid User")
        verified = self._verify_code(user, code)

        if not verified:
            raise ValidationError(detail="Invalid code.")

        if not user.email_verified:
            user.email_verified = True
            user.save()

        # return magic link token
        magic_token = user.generate_magic_link(sent_notification=False)
        data = {
            "user_id": user.idencode,
            "token": magic_token.key,
            "salt": magic_token.idencode,
            "type": user.type,
        }

        return success_response(data)

    @staticmethod
    def _verify_code(user, code):
        """Verify code against user."""
        try:
            token = ValidationToken.objects.get(
                user__id=user.id, key=code, type=VTOKEN_TYPE_OTP
            )
        except ValidationToken.DoesNotExist:
            return False

        # check code is valid or not.
        if not token.is_valid:
            return False

        # invalidate the code if successfully validated.
        token.invalidate()
        return True


class InviteeUserViewSet(
    mixins.UpdateModelMixin, mixins.ListModelMixin, GenericViewSet
):
    """API view to get and update."""

    permission_classes = (LoginTOTP,)
    queryset = FairfoodUser.objects.all()
    serializer_class = InviteeUserSerializer

    def get_queryset(self):
        """Return single user object from request."""
        queryset = super().get_queryset()
        return queryset.filter(pk=self.request.user.id)

    def list(self, request, *args, **kwargs):
        """List only one object as a single object."""
        token = request.query_params.get("token")
        salt = request.query_params.get("salt")
        if not all([token, salt]):
            raise ValidationError(detail="token and salt required.")
        self.set_user(token, salt)
        return super().list(request, *args, **kwargs)

    @db_transaction.atomic
    def update(self, request, *args, **kwargs):
        """Updates the resource with the specified request data.

        This method overrides the parent's update method to include additional
        logic.

        Args:
        - request: The request object containing the update data.
        - *args: Additional positional arguments.
        - **kwargs: Additional keyword arguments.

        Returns:
        - A success response containing the updated data.

        Raises:
        - ValidationError: If the 'token' or 'salt' query parameters are
        missing.
        """

        token = request.query_params.get("token")
        salt = request.query_params.get("salt")

        # Validate 'token' and 'salt' parameters
        if not all([token, salt]):
            raise ValidationError(detail="token and salt required.")
        token = self.set_user(token, salt)
        token.invalidate()

        # Run parent update logic
        super().update(request, *args, **kwargs)

        # Activate node_member
        member = NodeMember.objects.filter(
            node=request.user.default_node, user=request.user
        ).first()
        if member:
            member.active = True
            member.save(update_fields=("active",))

        # Create a magic token.
        data = {
            "user_id": request.user.idencode,
            "type": request.user.type,
        }
        return success_response(data)

    def set_user(self, token, salt):
        """Update user with request."""

        # get token
        try:
            token = ValidationToken.objects.get(pk=decode(salt), key=token)
        except ValidationToken.DoesNotExist:
            raise ValidationError("Invalid Token")

        # check token validity
        if not token.is_valid:
            raise ValidationError("Invalid Token")
        self.request.user = token.user

        # updating kwargs for serializer context.
        self.kwargs["user"] = token.user
        self.kwargs["node"] = token.user.default_node
        return token


class GoogleLogin(views.APIView):
    """API for Google login."""

    def get(self, request, *args, **kwarg):
        """Authenticate with google code."""
        code = request.query_params.get("code", None)
        error = request.query_params.get("error", None)
        if error:
            raise ValidationError(detail=error)
        if not code:
            raise ValidationError(detail="Code id required.")

        # for redirect from google.
        host = f"{request.scheme}://{request.get_host()}" + reverse(
            "google-login"
        )
        access_token = self.google_get_access_token(code, host)

        user_info = self.google_get_user_info(access_token)
        user = self.get_user(user_info["email"])

        # check user in available.
        redirect_uri = self.generate_redirect_uri()
        if not user:
            redirect_uri += "?error=invalid_user"
        else:
            token = user.generate_magic_link(sent_notification=False)
            redirect_uri += (
                f"?token={token.key}"
                f"&user={user.idencode}"
                f"&salt={token.idencode}&type={user.type}"
            )
            if not user.email_verified:
                user.email_verified = True
                user.save()
        return redirect(redirect_uri)

    @staticmethod
    def get_user(email):
        """Get matching user from DB."""
        try:
            return USER_MODEL.objects.get(username__iexact=email)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def google_get_access_token(code, redirect_uri):
        """
        Returns Google access token.
        Reference:
         * 'https://developers.google.com/identity/protocols/oauth2/web
         -server#obtainingaccesstokens'
        """
        data = {
            "code": code,
            "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        response = requests.post(GOOGLE_ACCESS_TOKEN_OBTAIN_URL, data=data)

        if not response.ok:
            raise ValidationError(response.json())

        return response.json()["access_token"]

    @staticmethod
    def google_get_user_info(access_token):
        """Returns user info from Google.

        Reference: https://developers.google.com/identity/protocols/oauth2/
                    web-server#callinganapi
        """
        response = requests.get(
            GOOGLE_USER_INFO_URL, params={"access_token": access_token}
        )

        if not response.ok:
            raise ValidationError("Failed to obtain user info from Google.")

        return response.json()

    @staticmethod
    def generate_redirect_uri():
        """Returns the redirect uri according to the user type."""
        return settings.LOGIN_ROOT_URL + "/google-login/"


# accounts/admin/login
class FFAdminLogin(generics.CreateAPIView):
    """Login view."""

    permission_classes = (LoginTOTP,)
    serializer_class = auth_serializers.FFAdminLoginSerializer


# accounts/login/magic
class MagicLogin(generics.CreateAPIView):
    """Login with magic link."""

    # TODO: user IsValidationTokenValid permission
    permission_classes = (LoginTOTP,)
    serializer_class = auth_serializers.MagicLoginSerializer


# accounts/logout
class Logout(APIView):
    """View to logout."""

    permission_classes = (user_permissions.IsAuthenticated,)
    http_method_names = [
        "post",
    ]

    def post(self, request, user=None, *args, **kwargs):
        """Post method to logout.

        TODO: check and move to serializer

        Request Params:
            Body:
                device_id(str): optional device id to delete device.
            kwargs:
                account(obj): user account.
        Response:
            Success response.
        """
        device_id = request.data.get("device_id", None)
        user.logout(device_id)

        return comm_lib._success_response({}, "Logout successful", 200)


class ResetPassword(generics.CreateAPIView):
    """View to create reset password.

    TODO: change to send reset password link
    """

    permission_classes = (LoginTOTP,)

    def post(
        self, request, *args, **kwargs
    ):  # TODO: check and move to serializer
        """Post method to send password reset email."""
        try:
            user = FairfoodUser.objects.get(email=request.data["email"])
        except Exception:
            raise BadRequest("Invalid email, reset failed.")
        success = user.reset_password()
        if not success:
            raise BadRequest("Invalid email, reset failed.")

        return comm_lib._success_response({}, "Reset initiated.", 200)


class SetPassword(generics.CreateAPIView):
    """View to set password after forgot password."""

    permission_classes = (user_permissions.IsValidationTokenValid,)

    def post(self, request, *args, **kwargs):  # TODO: move to serializer
        """Post method to set user password."""
        password = request.data.get("password", None)
        if not password:
            raise BadRequest("Password not found")
        valid, message = comm_lib._validate_password(password)
        if not valid:
            raise BadRequest(message)
        tok_user = kwargs["token"].user
        tok_user.set_password(password)
        tok_user.save()
        kwargs["token"].mark_as_used()
        login = auth_serializers.LoginSerializer(kwargs["token"].user)

        return comm_lib._success_response(
            login.data, "Password reset successful. Please login", 200
        )


# accounts/magic/generate/
class MagicLink(generics.CreateAPIView):
    """View to generate magic link."""

    permission_classes = (LoginTOTP,)
    serializer_class = auth_serializers.MagicLinkSerializer


class VerificationEmail(generics.CreateAPIView):
    """View to verify the usr email."""

    permission_classes = (user_permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """Post method to resend verification email."""
        request.user.verify_email()

        return comm_lib._success_response({}, "Email sent successfully.", 200)


class CheckPassword(generics.RetrieveAPIView):
    """validate password view."""

    @staticmethod
    def post(request, *args, **kwargs):  # TODO: remove post
        """Overriding the create method."""

        user = authenticate(
            username=request.data["username"],
            password=request.data["password"],
        )
        if user:
            return comm_lib._success_response(
                {}, "Authentication successful", 200
            )
        else:
            raise BadRequest("Authentication failed.")
