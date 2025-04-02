"""Serializers for project details."""
from sentry_sdk import capture_exception
from common.drf_custom import fields as custom_fields
from common.drf_custom.serializers import DynamicModelSerializer
from common.exceptions import UnauthorizedAccess
from django.contrib.auth import authenticate
from django.db import transaction as django_transaction
from rest_framework import serializers
from v2.accounts import constants as acc_consts
from v2.accounts.models import FairfoodUser
from v2.projects import constants as proj_conts
from v2.projects.constants import INCOMING
from v2.projects.constants import OUTGOING
from v2.projects.models import NodeCard
from v2.projects.models import Payment
from v2.projects.models import PremiumOption
from v2.projects.models import Project
from v2.projects.models import ProjectPremium
from v2.projects.models import ProjectProduct
from v2.supply_chains.models import NodeMember
from v2.supply_chains.serializers.node import NodeSerializer
from v2.supply_chains.serializers.public import SupplyChainSerializer


class PremiumOptionSerializer(DynamicModelSerializer):
    """Serializer for the PremiumOption model.

    This serializer provides dynamic serialization based on the model's
    fields.
    """

    class Meta:
        model = PremiumOption
        fields = "__all__"


class ProjectPremiumSerializer(DynamicModelSerializer):
    """Serializer project premium details."""

    owner_details = NodeSerializer(
        source="owner", fields=("id", "full_name"), read_only=True
    )
    options = PremiumOptionSerializer(
        source="active_options",
        many=True,
        fields=("id", "name", "amount"),
        read_only=True,
    )

    class Meta:
        model = ProjectPremium
        fields = (
            "id",
            "name",
            "type",
            "amount",
            "included",
            "dependant_on_card",
            "applicable_activity",
            "owner_details",
            "category",
            "options",
            "calculation_type",
            "is_active",
        )


class ProjectProductSerializer(serializers.ModelSerializer):
    """Serializer for project products."""

    id = custom_fields.IdencodeField(read_only=True, source="product.id")
    name = serializers.CharField(source="product.name")
    description = serializers.CharField(source="product.description")
    premiums = custom_fields.ManyToManyIdencodeField()

    class Meta:
        model = ProjectProduct
        fields = (
            "id",
            "name",
            "description",
            "image",
            "price",
            "currency",
            "premiums",
            "is_active",
        )


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for project details."""

    id = custom_fields.IdencodeField(read_only=True)
    owner = custom_fields.IdencodeField()
    supply_chain = custom_fields.IdencodeField(
        serializer=SupplyChainSerializer
    )
    # products = custom_fields.ManyToManyIdencodeField(
    #     serializer=ProjectProductSerializer, source='product_objects')
    premiums = ProjectPremiumSerializer(many=True)

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "description",
            "image",
            "owner",
            "supply_chain",
            "premiums",
            "currency",
            "buy_enabled",
            "sell_enabled",
            "quality_correction",
            "show_price_comparison",
        )


class NodeCardSerializer(DynamicModelSerializer):
    """Serializer project premium details."""
    fairid = serializers.CharField(required=False, allow_blank=True)
    card_id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = NodeCard
        fields = ("id", "node", "status", "card_id", "fairid", "external_id")

    @django_transaction.atomic
    def create(self, validated_data):
        """Overriding the create method.

        We are trying to fetch the cards with same hex id and change the
        node if it is already there. This will help us to pre-load all
        the cards and their fairid to the system and set it's node to
        none. When someone attach a card then node will get assigned.
        """
        # get user from request.
        user = (
            self.context["request"].user 
            if "request" in self.context 
            else self.context["user"] 
            if "user" in self.context 
            else None
        )
        self.deactivate_old_cards(validated_data["node"])
        external_id = validated_data.get("external_id", None)
        card_id = validated_data.get("card_id")
        fairid = validated_data.get("fairid")
        try:
            if card_id:
                card = NodeCard.objects.get(card_id=card_id)
            else:
                card = NodeCard.objects.get(fairid=fairid)
            card.updater = user
            card.node = validated_data["node"] 
            card.status = proj_conts.CARD_STATUS_ACTIVE
            card.external_id = external_id
            card.card_id = card_id or ""
            card.fairid = fairid or ""
            card.save()
        except NodeCard.DoesNotExist:
            card = NodeCard.objects.create(
                card_id=card_id or "", 
                creator=user,
                node=validated_data["node"],
                status=proj_conts.CARD_STATUS_ACTIVE,  
                external_id=external_id,
                fairid=fairid or ""
            )
        except Exception as e:
            capture_exception(e)
        card.node.updated_on = card.updated_on
        card.node.save()
        return card

    @staticmethod
    def deactivate_old_cards(node):
        """Set status CARD_STATUS_INACTIVE to previous cards."""
        old_cards = NodeCard.objects.filter(node=node)
        if old_cards.exists():
            old_cards.update(status=proj_conts.CARD_STATUS_INACTIVE)


class AppLoginSerializer(serializers.Serializer):
    """Serializer to App login."""

    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    device_id = serializers.CharField(required=True, write_only=True)
    device_type = serializers.IntegerField(
        default=acc_consts.DEVICE_TYPE_ANDROID, write_only=True
    )
    registration_id = serializers.CharField(required=False, write_only=True)
    name = serializers.CharField(required=True, write_only=True)
    force_logout = serializers.BooleanField(default=False, write_only=True)

    id = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    is_granted = serializers.BooleanField(read_only=True)
    token = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    email_verified = serializers.BooleanField(read_only=True)
    terms_accepted = serializers.BooleanField(read_only=True)
    last_active_device = serializers.DictField(
        child=serializers.CharField(), read_only=True
    )

    def create(self, validated_data):
        """Overriding the create method."""
        user = authenticate(
            username=validated_data["username"],
            password=validated_data["password"],
        )
        if not user:
            raise UnauthorizedAccess("Invalid email or password")
        if not user.nodes.exists():
            raise UnauthorizedAccess("User does not have access to any nodes")
        return self._generate_login_response(user, validated_data)

    def _generate_login_response(self, user, validated_data):
        """Function to return login user device details.

        check user is active on any other device.and if user
        is active return force_logout as True and is_granted as
        False and pass active device details.

        Validated_data:
        user: user obj.
        device_id: user device id.
        name: user device name.
        force_logout: boolean value if
        """
        refresh = self._set_refresh(user)
        device = user.get_or_create_device(validated_data)
        data = device.generate_token(validated_data["force_logout"], refresh)
        data["id"] = user.idencode
        data["type"] = user.type
        data["status"] = user.status
        data["email_verified"] = user.email_verified
        data["terms_accepted"] = user.terms_accepted
        data["last_active_device"] = self._get_device_details(user)
        return data

    @staticmethod
    def _get_device_details(user):
        """To get user device details."""
        device = user.active_mobile_device()
        data = {
            "name": "Unknown",
            "device_id": "",
            "registration_id": "",
            "type": "",
            "active": "",
        }
        if device:
            data["name"] = device.name
            data["device_id"] = device.device_id
            data["registration_id"] = device.registration_id
            data["type"] = device.type
            data["active"] = device.active
        return data

    @staticmethod
    def _set_refresh(user: FairfoodUser) -> bool:
        """Refresh token logic depends on the user, which has access on only
        buy_enabled projects."""
        nodes = NodeMember.objects.filter(user=user).values_list(
            "node", flat=True
        )
        projects = Project.objects.filter(owner_id__in=nodes)
        only_buy_enabled = projects.filter(
            buy_enabled=True, sell_enabled=False
        )

        if projects.count() == only_buy_enabled.count() != 0:
            return False
        return True


class PaymentSerializer(DynamicModelSerializer):
    """To Serialize payments."""

    source_details = NodeSerializer(
        source="source", read_only=True, fields=("id", "full_name", "image")
    )
    destination_details = NodeSerializer(
        source="destination",
        read_only=True,
        fields=("id", "full_name", "image"),
    )
    premium_details = ProjectPremiumSerializer(
        source="premium", fields=("id", "name"), read_only=True
    )
    direction = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = "__all__"

    def get_direction(self, instance):
        """Set direction according to the current node."""
        try:
            node = self.context["view"].kwargs.get("node")
        except KeyError:
            node = None

        if not node:
            return ""

        if instance.destination == node:
            return OUTGOING
        elif instance.source == node:
            return INCOMING
        else:
            return ""
