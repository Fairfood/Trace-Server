"""Serializers related to the user model."""
from autobahn.util import generate_user_password
from common.drf_custom import fields as custom_fields
from common.drf_custom.mixins import WriteOnceMixin
from common.drf_custom.serializers import CircularSerializer
from common.drf_custom.serializers import IdencodeModelSerializer
from common.exceptions import AccessForbidden
from common.exceptions import BadRequest
from common.library import _pop_out_from_dictionary
from common.library import _validate_password
from django.contrib.auth import authenticate
from django.db import transaction as db_transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from v2.accounts import validator as accounts_validator
from v2.accounts.models import FairfoodUser
from v2.accounts.models import Person
from v2.accounts.models import TermsAndConditions
from v2.accounts.models import UserDevice
from v2.supply_chains.models import AdminInvitation
from v2.supply_chains.models import Company
from v2.supply_chains.models import Node

from .other_apps import UserNodeSerializer


class UserSerializer(WriteOnceMixin, serializers.ModelSerializer):
    """Serializer for user."""

    id = custom_fields.IdencodeField(read_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()  # TODO: change to write_once field
    updated_email = serializers.CharField(required=False, allow_blank=True)
    dob = serializers.DateField(required=False)
    phone = custom_fields.PhoneNumberField(required=False, allow_blank=True)
    address = serializers.CharField(required=False)
    image = custom_fields.RemovableImageField(required=False, allow_blank=True)
    type = serializers.IntegerField(required=False)
    status = serializers.IntegerField(required=False)

    terms_accepted = serializers.BooleanField(required=False)
    privacy_accepted = serializers.BooleanField(required=False)
    email_verified = serializers.BooleanField(required=False)

    password = serializers.CharField(write_only=True, required=False)
    current_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)

    default_node = custom_fields.IdencodeField(
        required=False, related_model=Node
    )
    nodes = custom_fields.ManyToManyIdencodeField(
        serializer=UserNodeSerializer, read_only=True, source="usernodes"
    )

    class Meta:
        """Meta info."""

        # TODO: remove unwanted field. check required fields

        model = FairfoodUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "dob",
            "phone",
            "address",
            "password",
            "terms_accepted",
            "privacy_accepted",
            "email_verified",
            "status",
            "image",
            "default_node",
            "current_password",
            "new_password",
            "updated_email",
            "nodes",
            "type",
        ]

        write_once_fields = ("type", "user", "password", "email_verified")

    def validate_email(self, value):
        """To perform function validate_email."""
        if value:
            value = value.lower()
        return value

    def validate_username(self, value):
        """To validate username."""
        validator = accounts_validator.validate_username(value)
        if not validator["valid"]:
            raise serializers.ValidationError("Invalid username")
        if not validator["available"]:
            raise serializers.ValidationError("Email already taken")
        return value

    def update_password(self, instance, validated_data):
        """To update password."""
        if "current_password" not in validated_data.keys():
            raise BadRequest("Old password is required to update password")
        if not authenticate(
            username=instance.email,
            password=validated_data["current_password"],
        ):
            raise AccessForbidden("Old password supplied is wrong")
        valid, errors = _validate_password(validated_data["new_password"])
        if not valid:
            raise BadRequest(errors)
        instance.set_password(validated_data["new_password"])
        instance.save()
        return True

    def update(self, instance, validated_data):
        """Overriding default update method.

        Update user details and the django user details..
        """
        if "email" in validated_data.keys():
            instance.request_email_update(validated_data.pop("email"))

        if "new_password" in validated_data.keys():
            self.update_password(instance, validated_data)
            _pop_out_from_dictionary(
                validated_data, ["current_password", "new_password"]
            )
        if "default_node" in validated_data:
            members = instance.usernodes.filter(
                node=validated_data["default_node"]
            )
            if not members.exists():
                raise AccessForbidden(
                    "Invalid default_node. User does not have access to the"
                    " node."
                )
        super(UserSerializer, self).update(instance, validated_data)
        if "default_node" in validated_data:
            instance.default_node.update_date_joined()
            admin_invite = AdminInvitation.objects.filter(
                invitee=instance.default_node
            ).first()
            if admin_invite:
                admin_invite.log_joined_activity()
            members = instance.usernodes.filter(
                node=validated_data["default_node"]
            )
            for member in members:
                member.active = True
                member.save()
        return instance

    def create(self, validated_data):
        """Overriding the create method."""
        self.validate_username(validated_data["email"])
        # TODO: move to validate_
        if (
            "username" not in validated_data.keys()
            or not validated_data["username"]
        ):
            validated_data["username"] = validated_data["email"]
        validated_data["first_name"] = validated_data["first_name"].title()
        validated_data["last_name"] = validated_data["last_name"].title()
        extra_keys = list(
            set([field.name for field in FairfoodUser._meta.get_fields()])
            ^ set([*validated_data])
        )

        _pop_out_from_dictionary(validated_data, extra_keys)
        user = FairfoodUser.objects.create(**validated_data)
        if "password" in validated_data.keys():
            user.set_password(validated_data["password"])
        else:
            user.set_password(generate_user_password())
            user.save()
        if self.context.get("view", None):
            user.verify_email()  # TODO: change to a context variable

        return user


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user."""

    # TODO: combine to user details serializer using min mode
    id = custom_fields.IdencodeField(read_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()
    phone = custom_fields.PhoneNumberField(required=False, allow_blank=True)
    image = custom_fields.RemovableImageField(required=False, allow_blank=True)

    class Meta:
        """Meta info."""

        model = FairfoodUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "image",
            "type",
            "is_active",
        ]


class UserDeviceSerializer(WriteOnceMixin, serializers.ModelSerializer):
    """Serializer of user device model."""

    id = serializers.SerializerMethodField()  # TODO: change to idencode field

    class Meta:
        """Meta info."""

        model = UserDevice
        fields = "__all__"
        extra_kwargs = {
            "device_id": {"required": True},
            "creator": {"write_only": True},
            "updater": {"write_only": True},
            "user": {"write_only": True},
        }

    def get_id(self, obj):
        """Get encoded  id."""
        return obj.idencode

    def create(self, validated_data):
        """Overriding the create method."""
        for device in UserDevice.objects.filter(
            device_id=validated_data["device_id"]
        ):
            if device.user.type == validated_data["user"].type:
                device.active = False
                device.updater = validated_data["user"]
                device.save()

        try:
            device = UserDevice.objects.get(
                device_id=validated_data["device_id"],
                user=validated_data["user"],
            )
            device.registration_id = validated_data.get(
                "registration_id", device.registration_id
            )
            device.type = validated_data.get("type", device.type)
            device.name = validated_data.get("name", device.name)
            device.updater = validated_data["user"]
            device.active = True
            device.save()
            return device
        except Exception:
            device = UserDevice.objects.create(**validated_data)
            return device


class AbstractPersonSerializer(serializers.ModelSerializer):
    """Serializer for Abstract Person model."""

    id = custom_fields.IdencodeField(read_only=True)

    class Meta:
        abstract = True
        fields = (
            "first_name",
            "last_name",
            "gender",
            "dob",
            "birth_city",
            "marital_status",
            "email",
            "phone",
        )


class PersonSerializer(AbstractPersonSerializer):
    """Serializer for Person model."""

    id = custom_fields.IdencodeField(read_only=True)
    phone = custom_fields.PhoneNumberField(required=False, allow_blank=True)

    class Meta:
        model = Person
        fields = (
            "first_name",
            "last_name",
            "gender",
            "dob",
            "birth_city",
            "marital_status",
            "email",
            "phone",
        )

    @staticmethod
    def has_changed(instance, field_name, value):
        """To perform function has_changed."""
        return not getattr(instance, field_name) == value

    def get_changed_fields(instance, validated_data):
        """To perform function get_changed_fields."""
        field_titles = {
            "first_name": "contact info",
            "last_name": "contact info",
            "gender": "contact info",
            "dob": "contact info",
            "birth_city": "contact info",
            "marital_status": "contact info",
            "email": "contact info",
            "phone": "contact info",
            "image": "image",
        }
        changed_fields = []
        for field_name, value in validated_data.items():
            if PersonSerializer.has_changed(instance, field_name, value):
                changed_fields.append(field_titles.get(field_name, ""))
        return list(set(changed_fields))


class TermsAndConditionsSerializer(serializers.ModelSerializer):
    """Class to handle TermsAndConditionsSerializer and functions."""

    class Meta:
        model = TermsAndConditions
        fields = ("title", "version")


class InviteeUserSerializer(IdencodeModelSerializer):
    """Serializer for accept invitation."""

    default_node = CircularSerializer(
        related_model=Company,
        module="v2.supply_chains.serializers",
        serializer_class="node.CompanySerializer",
        required=False,
    )
    nodes = UserNodeSerializer(source="usernodes", read_only=True, many=True)
    # invitation_type = SerializerMethodField()

    class Meta:
        model = FairfoodUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "default_node",
            "nodes",
            "terms_accepted",
            "privacy_accepted",
            "email_verified",
        ]

    def get_fields(self):
        """Update default_node serializer with context."""
        fields = super().get_fields()
        default_node = fields["default_node"]
        default_node.kwargs["context"] = self.context
        return fields

    @db_transaction.atomic
    def update(self, instance, validated_data):
        """Update data while accepting invitation."""
        default_node = validated_data.pop("default_node", None)

        # Update node details if any updates.
        if default_node:
            default_node_field = self.fields.pop("default_node")
            default_node_field.update(instance.default_node, default_node)

        # default auto check values
        validated_data["terms_accepted"] = True
        validated_data["privacy_accepted"] = True
        validated_data["email_verified"] = True

        # Updating instance with validated data.
        instance = super(InviteeUserSerializer, self).update(
            instance, validated_data
        )

        # update_password
        instance.set_password(generate_user_password())
        instance.save()

        return instance

    def create(self, validated_data):
        """by-passing create."""
        raise ValidationError("Not Implemented.")
