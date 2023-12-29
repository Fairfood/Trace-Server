"""Serializers related to themes."""
from common import library as comm_lib
from common.drf_custom import fields as custom_fields
from django.utils import translation
from rest_framework import serializers
from v2.dashboard.models import CITheme
from v2.dashboard.models import ConsumerInterfaceProduct
from v2.dashboard.models import ConsumerInterfaceStage
from v2.dashboard.models import DashboardTheme
from v2.dashboard.models import MenuItem
from v2.products.models import Batch
from v2.products.models import Product
from v2.supply_chains.models import Node
from v2.supply_chains.models import Operation
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.serializers.public import SupplyChainSerializer


class CIValidateBatchSerializer(serializers.Serializer):
    """Serializer to check if a batch can be added to a theme."""

    batch = serializers.IntegerField()
    supply_chains = custom_fields.ManyToManyIdencodeField(
        related_model=SupplyChain
    )
    node = custom_fields.KWArgsObjectField(related_model=Node)

    def validate_batch(self, value):
        """Validate Batch."""
        batch = Batch.objects.filter(number=value).first()
        if not batch:
            raise serializers.ValidationError("Invalid batch number")
        return batch

    def validate(self, attrs):
        """Validate data."""
        batch = attrs["batch"]
        supply_chains = attrs["supply_chains"]
        node = attrs["node"]
        if batch.product.supply_chain not in supply_chains:
            raise serializers.ValidationError(
                "Batch is not from given supply chains."
            )
        if not batch.node == node:
            batch_chain = batch.node.get_chain(
                supply_chain=batch.product.supply_chain, include_self=True
            )
            if node not in batch_chain:
                raise serializers.ValidationError(
                    "Node not involved in the chain of the batch."
                )
        return attrs

    def update(self, instance, validated_data):
        """Update overridden."""
        raise NotImplementedError

    def create(self, validated_data):
        """Create overridden."""
        return True

    def to_representation(self, instance):
        """Representation  of data."""
        return {"status": "Success", "message": "Batch id Valid"}


class ConsumerInterfaceStageSerializer(serializers.ModelSerializer):
    """Serializer for ConsumerInterfaceStage."""

    id = custom_fields.IdencodeField(read_only=True)
    theme = custom_fields.IdencodeField(related_model=CITheme)
    operation = custom_fields.IdencodeField(related_model=Operation)

    class Meta:
        model = ConsumerInterfaceStage
        fields = (
            "id",
            "theme",
            "operation",
            "title",
            "image",
            "description",
            "actor_name",
            "position",
            "map_zoom_level",
            "map_latitude",
            "map_longitude",
        )


class ConsumerInterfaceProductSerializer(serializers.ModelSerializer):
    """Serializer for ConsumerInterfaceStage."""

    id = custom_fields.IdencodeField(read_only=True)
    theme = custom_fields.IdencodeField(related_model=CITheme)
    product = custom_fields.IdencodeField(related_model=Product)

    class Meta:
        model = ConsumerInterfaceProduct
        fields = (
            "id",
            "theme",
            "product",
            "name",
            "image",
            "description",
            "location",
        )


class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer for ConsumerInterfaceStage."""

    id = custom_fields.IdencodeField(read_only=True)
    theme = custom_fields.IdencodeField(related_model=CITheme)

    class Meta:
        model = MenuItem
        fields = ("id", "theme", "title", "url", "target", "position")


class CIThemeSerializer(serializers.ModelSerializer):
    """Serializer to return theme of an entity."""

    id = custom_fields.IdencodeField(read_only=True)
    name = serializers.CharField(required=True)
    batch = serializers.IntegerField(required=False, write_only=True)
    node = custom_fields.IdencodeField(required=False)
    supply_chains = custom_fields.ManyToManyIdencodeField(
        related_model=SupplyChain, serializer=SupplyChainSerializer
    )
    base_theme = custom_fields.IdencodeField(
        write_only=True, related_model=CITheme, required=False
    )
    brand_logo = custom_fields.NullableFileField(
        allow_null=True, required=False
    )
    banner_image = custom_fields.NullableFileField(
        allow_null=True, required=False
    )

    menu_items = custom_fields.ManyToManyIdencodeField(
        serializer=MenuItemSerializer, read_only=True
    )
    products = custom_fields.ManyToManyIdencodeField(
        serializer=ConsumerInterfaceProductSerializer, read_only=True
    )
    stages = custom_fields.ManyToManyIdencodeField(
        serializer=ConsumerInterfaceStageSerializer, read_only=True
    )

    def_theme = None

    class Meta:
        model = CITheme
        exclude = ("creator", "updater", "created_on", "updated_on")

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        self.def_theme = CITheme.objects.filter(is_public=True).first()
        return super(CIThemeSerializer, self).__init__(*args, **kwargs)

    def validate_name(self, value):
        """Validate name."""
        if CITheme.objects.filter(name=value).exists() and not self.instance:
            raise serializers.ValidationError("Theme name already taken.")
        return value

    def validate_batch(self, value):
        """Validate batch."""
        try:
            return Batch.objects.get(number=value)
        except Batch.DoesNotExist:
            raise serializers.ValidationError("Invalid Batch Number")

    def validate_brand_logo(self, value):
        """Validate brand_logo."""
        if value:
            return value
        return self.def_theme.brand_logo

    def validate_banner_image(self, value):
        """Validates banner image."""
        if value:
            return value
        return self.def_theme.banner_image

    def create(self, validated_data):
        """Create overridden."""
        base_theme = validated_data.pop("base_theme", self.def_theme)
        if "node" not in validated_data or not validated_data["node"]:
            if "node" not in self.context["view"].kwargs:
                raise serializers.ValidationError("Node ID is required")
            validated_data["node"] = self.context["view"].kwargs["node"]
        theme = base_theme.create_copy()
        theme.name = validated_data["name"]
        theme.node = validated_data["node"]
        for sc in validated_data["supply_chains"]:
            theme.supply_chains.add(sc)
        theme.save()
        return theme

    def update(self, instance, validated_data):
        """Override update for public theme validation."""
        if instance.is_public:
            raise serializers.ValidationError("Cannot update public theme")
        return super(CIThemeSerializer, self).update(instance, validated_data)

    def to_representation(self, instance):
        """Response representation."""
        data = super(CIThemeSerializer, self).to_representation(instance)
        data["batch"] = instance.batch.number if instance.batch else None
        return data


class PublicThemeSerializer(serializers.ModelSerializer):
    """Serializer to return theme of an entity."""

    id = custom_fields.IdencodeField()
    batch = custom_fields.IdencodeField()
    menu_items = custom_fields.ManyToManyIdencodeField(
        serializer=MenuItemSerializer
    )
    available_languages = custom_fields.ListRepresentationField()

    class Meta:
        model = CITheme
        # Excluding translation field.
        exd_trans_fls = [
            f.name
            for f in model._meta.fields
            if f.__class__.__name__ == "TranslationCharField"
        ]
        exclude = [
            "node",
            "creator",
            "updater",
            "created_on",
            "updated_on",
        ] + exd_trans_fls

    def to_representation(self, theme):
        """Response representation."""
        theme.check_language_rollback()
        data = super(PublicThemeSerializer, self).to_representation(theme)
        data["current_language"] = translation.get_language()
        encoded_batch_id = self.context["request"].query_params.get(
            "batch", None
        )
        batch_id = comm_lib._decode(encoded_batch_id)
        if not batch_id:
            return data
        data["batch"] = encoded_batch_id
        return data

        # Note: Due to performance issue following lines are commented.
        # batch = Batch.objects.get(id=batch_id)

        # batch_chain = batch.node.get_chain(
        #         supply_chain=batch.product.supply_chain, include_self=True)
        # if theme.node in batch_chain:
        #     return data
        #
        # raise AccessForbidden("Batch cannot be traced with this theme")


class DashboardThemeSerializer(serializers.ModelSerializer):
    """Serializer for dashboard theme."""

    id = custom_fields.IdencodeField(read_only=True)
    node = custom_fields.IdencodeField(write_only=True, required=False)
    image = serializers.FileField(
        max_length=None, allow_empty_file=True, allow_null=True, required=False
    )

    class Meta:
        model = DashboardTheme
        fields = (
            "id",
            "node",
            "image",
            "colour_primary_alpha",
            "colour_primary_beta",
            "colour_primary_gamma",
            "colour_primary_delta",
            "colour_secondary",
            "colour_font_alpha",
            "colour_font_beta",
            "colour_font_negative",
            "colour_border_alpha",
            "colour_border_beta",
            "colour_background",
            "colour_sidebar",
            "colour_map_background",
            "colour_map_clustor",
            "colour_map_marker",
            "colour_map_selected",
            "colour_map_marker_text",
        )

    def validate_node(self, node):
        """Validate node."""
        if not self.instance and not node:
            raise serializers.ValidationError(
                "Node ID is required to create theme"
            )

    def create(self, validated_data):
        """Create overridden."""
        dashboard_data = DashboardTheme.objects.create(**validated_data)
        return dashboard_data
