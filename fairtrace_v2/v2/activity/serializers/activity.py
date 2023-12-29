"""Serializers for activity APIs."""
from common.drf_custom import fields as custom_fields
from rest_framework import serializers
from v2.activity.models import Activity


class NodeActivitySerializer(serializers.ModelSerializer):
    """Serializer for Activities."""

    text = serializers.CharField(source="node_text")
    supply_chain = custom_fields.IdencodeField()
    username = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ("text", "created_on", "supply_chain", "username", "image")

    @staticmethod
    def get_username(instance):
        """Returns username."""
        return instance.user.username if instance.user else None

    @staticmethod
    def get_image(instance):
        """Returns image_url."""
        return instance.user.image_url if instance.user else None


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for Activities."""

    text = serializers.CharField(source="user_text")
    supply_chain = custom_fields.IdencodeField()

    class Meta:
        model = Activity
        fields = ("text", "created_on", "supply_chain")
