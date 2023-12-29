"""Serializers for transparency requests to be imported from other apps."""
from common.drf_custom import fields as custom_fields
from rest_framework import serializers
from v2.transparency_request.models import StockRequest


class StockRequestBasicSerializer(serializers.ModelSerializer):
    """Serializer for creating and retrieving stock request details."""

    id = custom_fields.IdencodeField(read_only=True)
    number = serializers.IntegerField(read_only=True)
    status = serializers.IntegerField(read_only=True)
    requester = custom_fields.IdencodeField()
    requestee = custom_fields.IdencodeField()
    product = custom_fields.IdencodeField()
    transaction = custom_fields.IdencodeField()
    claims = custom_fields.ManyToManyIdencodeField()

    class Meta:
        model = StockRequest
        fields = (
            "id",
            "number",
            "status",
            "requester",
            "requestee",
            "product",
            "transaction",
            "claims",
            "created_on",
            "quantity",
            "unit",
            "price",
            "currency",
        )

    def to_representation(self, instance):
        """To perform function to_representation."""
        data = super(StockRequestBasicSerializer, self).to_representation(
            instance
        )
        data["product"] = {
            "id": instance.product.idencode,
            "name": instance.product.name,
            "supply_chain": instance.product.supply_chain.name,
        }
        return data
