"""Serializers for transparency request related APIs."""
from common.drf_custom import fields as custom_fields
from rest_framework import serializers
from v2.supply_chains.models import Node
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.transparency_request.models import TransparencyRequest


class TransparencyRequestSerializer(serializers.ModelSerializer):
    """Serializer retrieving transaction request details."""

    id = custom_fields.IdencodeField(read_only=True)
    number = serializers.IntegerField(read_only=True)
    request_type = serializers.IntegerField(read_only=True)
    requestee = custom_fields.IdencodeField(
        related_model=Node, serializer=NodeBasicSerializer
    )
    requester = custom_fields.IdencodeField(
        related_model=Node, serializer=NodeBasicSerializer
    )

    class Meta:
        model = TransparencyRequest
        exclude = ("deleted",)
