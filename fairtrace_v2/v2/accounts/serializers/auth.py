"""Serializers related to the user model."""
import datetime

from common.exceptions import AccessForbidden
from common.exceptions import BadRequest
from common.exceptions import UnauthorizedAccess
from common.library import _validate_password
from common.library import decode
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from sentry_sdk import capture_exception
from v2.accounts import validator as accounts_validator
from v2.accounts.constants import USER_TYPE_FAIRFOOD_ADMIN
from v2.accounts.constants import VTOKEN_TYPE_MAGIC_LOGIN
from v2.accounts.models import FairfoodUser
from v2.accounts.models import ValidationToken
from v2.accounts.serializers import user as user_serializers


class ValidateUsernameSerializer(serializers.Serializer):
    """Serializer to check the username availability."""

    username = serializers.CharField()

    def to_representation(self, obj):
        """Overriding the value returned when returning the serializer."""
        username = obj["username"].lower()
        response = accounts_validator.validate_username(username)
        return response


class ValidatePasswordSerializer(serializers.Serializer):
    """Serializer to check the password validity."""

    password = serializers.CharField()

    def to_representation(self, obj):
        """Overriding the value returned when returning the serializer."""
        response = {}
        response["valid"], response["message"] = _validate_password(
            obj["password"]
        )
        return response


class LoginSerializer(serializers.Serializer):
    """Serializer to login."""

    username = serializers.CharField()
    password = serializers.CharField()
    device_id = serializers.CharField()
    registration_id = serializers.CharField(required=False)
    name = serializers.CharField(required=False)

    def create(self, validated_data):
        """Overriding the create method."""
        user = authenticate(
            username=validated_data["username"],
            password=validated_data["password"],
        )
        if not user:
            raise UnauthorizedAccess("Invalid email or password")
        # If a user has no node after 1 hour from signUp then
        # User does not have access to any nodes.

        time_threshold = timezone.now() - datetime.timedelta(hours=1)
        if not user.is_fairtrace_admin:
            if user.date_joined <= time_threshold:
                if not user.nodes.exists():
                    raise UnauthorizedAccess(
                        "User does not have access to any nodes"
                    )

        validated_data["user"] = user.id
        device_serializer = user_serializers.UserDeviceSerializer(
            data=validated_data
        )
        if device_serializer.is_valid():
            device_serializer.save()
        else:
            raise BadRequest(device_serializer.errors)
        return user

    def to_representation(self, obj):
        """Overriding the value returned when returning the serializer."""
        token = obj.generate_magic_link(sent_notification=False)
        data = {
            "user_id": obj.idencode,
            "token": token.key,
            "salt": token.idencode,
            "type": obj.type,
        }
        return data


class FFAdminLoginSerializer(serializers.Serializer):
    """Serializer to login."""

    username = serializers.CharField()
    password = serializers.CharField()
    device_id = serializers.CharField()
    registration_id = serializers.CharField(required=False)
    name = serializers.CharField(required=False)

    def validate_username(self, value):
        """To perform function validate_username."""
        value = value.lower()
        return value

    def create(self, validated_data):
        """Overriding the create method."""
        user = authenticate(
            username=validated_data["username"],
            password=validated_data["password"],
        )
        if not user or user.type != USER_TYPE_FAIRFOOD_ADMIN:
            raise UnauthorizedAccess("Invalid email or password")
        validated_data["user"] = user.id
        device_serializer = user_serializers.UserDeviceSerializer(
            data=validated_data
        )
        if device_serializer.is_valid():
            device_serializer.save()
        else:
            raise BadRequest(device_serializer.errors)
        return user

    def to_representation(self, obj):
        """Overriding the value returned when returning the serializer."""
        data = {
            "token": obj.issue_access_token(),
            "id": obj.idencode,
            "type": obj.type,
            "status": obj.status,
            "email_verified": obj.email_verified,
            "terms_accepted": obj.terms_accepted,
        }
        return data


class MagicLinkSerializer(serializers.Serializer):
    """Serializer to generate magic link and send email."""

    email = serializers.EmailField(write_only=True)

    def validate_email(self, value):
        """To perform function validate_email."""
        if value:
            value = value.lower()
        return value

    def create(self, validated_data):
        """Overriding create method to generate magic link and send email."""
        # TODO: change to try except

        user = FairfoodUser.objects.filter(
            email=validated_data["email"]
        ).first()
        if not user:
            raise BadRequest("User is not registered")
        user.generate_magic_link()
        return {"status": True, "message": "Magic link sent"}


class MagicLoginSerializer(serializers.Serializer):
    """Serializer to login with magic link."""

    validation_token = serializers.CharField()
    salt = serializers.CharField()
    user_id = serializers.CharField()
    device_id = serializers.CharField()
    registration_id = serializers.CharField(required=False)
    name = serializers.CharField(required=False)

    def create(self, validated_data):
        """Overriding the create method."""
        # TODO: change to validate_ method
        # TODO: change to not send user ID in link
        try:
            user_id = decode(validated_data["user_id"])
            pk = decode(validated_data["salt"])
            try:
                token = ValidationToken.objects.get(
                    pk=pk,
                    user__id=user_id,
                    key=validated_data["validation_token"],
                    type=VTOKEN_TYPE_MAGIC_LOGIN,
                )
            except ValidationToken.DoesNotExist:
                raise ValidationError("Invalid token")
            if token.is_valid:
                token.invalidate()
                user = token.user
                if user.is_fairtrace_admin and not user.email_verified:
                    user.email_verified = True
                    user.save()
                validated_data["user"] = user.id
                device_serializer = user_serializers.UserDeviceSerializer(
                    data=validated_data
                )
                if device_serializer.is_valid():
                    device_serializer.save()
                else:
                    raise BadRequest(device_serializer.errors)
            else:
                user = None
        except Exception as e:
            capture_exception(e)
            user = None
        if not user:
            raise AccessForbidden("Login failed. Try again.")
        if not user.is_fairtrace_admin and not user.nodes.exists():
            raise UnauthorizedAccess("User does not have access to any nodes")
        return user

    def to_representation(self, obj):
        """Overriding the value returned when returning the serializer."""
        data = {
            "token": obj.issue_access_token(),
            "id": obj.idencode,
            "status": obj.status,
            "email_verified": obj.email_verified,
            "terms_accepted": obj.terms_accepted,
            "type": obj.type,
        }
        return data
