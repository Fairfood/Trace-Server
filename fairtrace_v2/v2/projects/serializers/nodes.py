"""Seralizers for nodes in project."""
from common.country_data import COUNTRIES
from common.drf_custom import fields as custom_fields
from common.drf_custom.serializers import DynamicModelSerializer
from common.library import get_acronym
from rest_framework import serializers
from v2.projects import constants
from v2.projects.models import NodeCard, ProjectNode
from v2.supply_chains.models import Farmer, Invitation, Operation
from v2.supply_chains.serializers.node import (CompanySerializer,
                                               FarmerSerializer)
from v2.supply_chains.serializers.supply_chain import FarmerInviteSerializer

from .project import NodeCardSerializer


class ProjectFarmerInviteSerializer(FarmerInviteSerializer):
    """Serializer to invite a farmer onto a project."""

    project = custom_fields.KWArgsObjectField(write_only=True, required=False)
    primary_operation = serializers.CharField(required=False)
    id_no = serializers.CharField(required=False, allow_null=True)
    supply_chain = serializers.CharField(required=False)
    is_created = serializers.BooleanField(default=True, required=False)
    country = serializers.CharField(required=True)
    id_no = serializers.CharField(required=False, allow_blank=True)

    class Meta(FarmerInviteSerializer.Meta):
        pass

    def validate(self, attrs):
        """Over ride to add dial code of the country selected to the phone
        number."""
        # Setting default for id_no
        attrs["id_no"] = attrs.get("id_no", "")
        country = attrs["country"]
        if "phone" in attrs.keys():
            phone = attrs["phone"]
            phone = phone.replace("+", "")
            dc = COUNTRIES[country]["dial_code"]
            if not phone.startswith(dc):
                attrs["phone"] = "+" + dc + phone
        if "country" in attrs and "province" in attrs:
            if (
                "latitude" not in attrs
                or "longitude" not in attrs
                or not attrs["latitude"]
                or not attrs["longitude"]
            ):
                attrs["latitude"] = COUNTRIES[attrs["country"]][
                    "sub_divisions"][attrs["province"]]["latlong"][0]
                attrs["longitude"] = COUNTRIES[attrs["country"]][
                    "sub_divisions"][attrs["province"]]["latlong"][1]
        if not self.context.get('skip_farmer_invite_validation', False):
            # Call the parent's validation (FarmerInviteSerializer)
            attrs = super(ProjectFarmerInviteSerializer, self).validate(attrs)
        return attrs

    def create(self, validated_data):
        """To perform function create."""
        project = validated_data.pop("project", None)
        validated_data.pop("is_created")
        # remove non db fields for filtering
        map_all_buyers = validated_data.pop("map_all_buyers", False)
        map_all_suppliers = validated_data.pop("map_all_suppliers", False)

        try:
            node = self.context["view"].kwargs["node"]
        except Exception:
            node = self.context["node"] 

        farmer = Farmer.objects.filter(**validated_data)
        # Check duplicate farmer exists or not. if exists then
        # return farmer Invitation object.
        if farmer:
            farmer_invite = Invitation.objects.filter(
                invitee=farmer[0]
            ).first()
            farmer_invite.is_created = False
            return farmer_invite

        sc = project.supply_chain if project else node.supply_chains.first()
        validated_data["supply_chain"] = sc
        validated_data["primary_operation"] = Operation.objects.get(
            name="Farmer"
        )
        # add removed non db fields
        validated_data["map_all_buyers"] = map_all_buyers
        validated_data["map_all_suppliers"] = map_all_suppliers

        # Currently hardcoded in API, so as to not hardcode in the App.
        # as of now, all farmers are added with their operation as farmer.
        # If the requirement changes, it might have to be sent from the app.
        farmer_invite = super(ProjectFarmerInviteSerializer, self).create(
            validated_data
        )
        farmer_invite.is_created = True
        node = farmer_invite.inviter
        buyers = node.get_buyers(supply_chain=sc)
        if project:
            buyers = project.member_nodes.filter(id__in=buyers)
        farmer_invite.connection.tag_buyers(buyers)
        if project:
            ProjectNode.objects.create(
                node=farmer_invite.invitee,
                project=project,
                connection=farmer_invite.connection,
            )
        return farmer_invite


class ProjectFarmerSerializer(FarmerSerializer):
    """Class to handle ProjectFarmerSerializer and functions."""

    projects = custom_fields.ManyToManyIdencodeField(
        source="participating_projects", read_only=True
    )
    cards = serializers.SerializerMethodField("get_cards")
    total_area_in_use = None
    all_crop_types = None
    total_income = None

    class Meta(FarmerSerializer.Meta):
        pass

    def get_cards(self, instance):
        """Function for filter latest active card details of farmer."""
        query_set = NodeCard.objects.filter(
            node=instance, status=constants.CARD_STATUS_ACTIVE
        ).order_by("-updated_on")[:1]
        serializer = NodeCardSerializer(instance=query_set, many=True)
        return serializer.data


class ProjectFarmerReadOnlySerializer(DynamicModelSerializer):
    """Serializer for read-only project farmer data.

    This serializer is used for representing project farmer data in a read-only
     format.
    It inherits from the `DynamicModelSerializer` class provided by the Django
    REST framework.

    Attributes:
    - cards: A read-only serializer method field that represents the associated
      cards related to the project farmer.
    - phone: A read-only custom phone number field that represents the phone
      number of the project farmer.

    Note:
    - This serializer assumes that the `DynamicModelSerializer` and
      `custom_fields` modules are correctly imported and available.
    - The `cards` field is expected to be implemented as a serializer method
      field, which means it should have a corresponding method named
      `get_cards()` defined within the serializer class.
    - The `phone` field is a read-only custom field named `PhoneNumberField`
      from the `custom_fields` module, which should handle the logic for
      representing the phone number in a specific format.
    """

    cards = serializers.SerializerMethodField()
    phone = custom_fields.PhoneNumberField(read_only=True)

    class Meta:
        model = Farmer
        fields = [
            "id",
            "name",
            "type",
            "phone",
            "street",
            "city",
            "country",
            "province",
            "zipcode",
            "image",
            "latitude",
            "longitude",
            "cards",
            "created_on",
            "updated_on",
            "id_no",
            "identification_no",
            "extra_fields",
        ]

    @staticmethod
    def get_cards(instance):
        """Function for filter the latest active card details of farmer."""
        query_set = NodeCard.objects.filter(
            node=instance, status=constants.CARD_STATUS_ACTIVE
        ).order_by("-updated_on")[:1]
        serializer = NodeCardSerializer(instance=query_set, many=True)
        return serializer.data


class ProjectCompanySerializer(CompanySerializer):
    """Class to handle ProjectCompanySerializer and functions."""

    projects = custom_fields.ManyToManyIdencodeField(
        source="participating_projects", read_only=True
    )
    cards = serializers.SerializerMethodField("get_cards")

    class Meta(CompanySerializer.Meta):
        pass

    def get_cards(self, instance):
        """Function for filter the latest active card details of farmer."""
        query_set = NodeCard.objects.filter(
            node=instance, status=constants.CARD_STATUS_ACTIVE
        ).order_by("-updated_on")
        serializer = NodeCardSerializer(instance=query_set, many=True)
        return serializer.data


class AppFarmerSerializer(serializers.ModelSerializer):
    """Serializer for Farmer model."""

    id = custom_fields.IdencodeField(read_only=True)
    name = serializers.CharField(required=False)
    phone = custom_fields.PhoneNumberField(required=False, allow_blank=True)

    class Meta:
        model = Farmer
        fields = (
            "id",
            "name",
            "house_name",
            "phone",
            "street",
            "city",
            "sub_province",
            "province",
            "country",
            "id_no",
        )

    def to_representation(self, instance):
        """To perform function to_representation."""
        language = self.context["view"].kwargs["language"]
        data = super(AppFarmerSerializer, self).to_representation(instance)
        data["name"] = get_acronym(data["name"])
        data["transaction_details"] = instance.transaction_count(language)
        return data

