"""Serializers for models from other apps.

Created to avoid cyclic import issues
"""
from common.drf_custom import fields as custom_fields
from common.drf_custom.serializers import IdencodeModelSerializer
from rest_framework import serializers
from v2.dashboard.models import CITheme
from v2.dashboard.models import DashboardTheme
from v2.supply_chains.models import Node
from v2.supply_chains.models import NodeMember


class DashboardThemeSerializer(serializers.ModelSerializer):
    """Serializer dashboard theme."""

    id = custom_fields.IdencodeField()

    class Meta:
        model = DashboardTheme
        fields = (
            "id",
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


class CiThemeSerializer(serializers.ModelSerializer):
    """Serializer for consumer interface theme."""

    id = custom_fields.IdencodeField()
    batch = custom_fields.IdencodeField()

    class Meta:
        model = CITheme
        fields = ("id", "name", "batch")


class UserNodeSerializer(IdencodeModelSerializer):
    """Serializer for node data in user details."""

    id = custom_fields.IdencodeField(source="node.id")
    name = serializers.CharField(source="node.full_name")
    node_type = serializers.IntegerField(source="node.type")
    member_role = serializers.IntegerField(source="type")
    profile_completion = serializers.FloatField(
        source="node.profile_completion"
    )
    image = serializers.FileField(source="node.image")
    theme = serializers.SerializerMethodField("get_theme")
    ci_themes = custom_fields.ManyToManyIdencodeField(
        serializer=CiThemeSerializer, source="node.themes"
    )
    selected_theme = serializers.IntegerField(source="node.selected_theme")
    available_languages = custom_fields.ListRepresentationField()

    class Meta:
        model = NodeMember
        fields = (
            "id",
            "name",
            "node_type",
            "member_role",
            "profile_completion",
            "image",
            "theme",
            "ci_themes",
            "selected_theme",
            "available_languages",
        )

    def get_theme(self, nodemember):
        """To perform function get_theme."""
        node = nodemember.node
        try:
            if node.features.dashboard_theming:
                return DashboardThemeSerializer(node.dashboard_theme).data
        except Node.features.RelatedObjectDoesNotExist:
            pass
        except Node.dashboard_theme.RelatedObjectDoesNotExist:
            pass
        return {}
