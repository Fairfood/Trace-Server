"""Serializers related to handling notifications."""
from common.drf_custom import fields as custom_fields
from rest_framework import serializers
from v2.communications.models import Notification
from v2.supply_chains.serializers.public import NodeBasicSerializer


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer to manage notification."""

    id = serializers.SerializerMethodField()
    actor_node = custom_fields.IdencodeField(serializer=NodeBasicSerializer)
    target_node = custom_fields.IdencodeField()
    supply_chain = custom_fields.IdencodeField()

    class Meta:
        """Meta info."""

        model = Notification
        exclude = ("send_to",)

        extra_kwargs = {
            "creator": {"write_only": True},
            "updater": {"write_only": True},
            "devices": {"write_only": True},
            "action": {"write_only": True},
            "action_url": {"write_only": True},
            "user": {"write_only": True},
        }

    def get_id(self, obj):
        """Get encoded  id."""
        return obj.idencode
