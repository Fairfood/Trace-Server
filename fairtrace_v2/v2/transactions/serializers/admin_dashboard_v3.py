from common.drf_custom.fields import RoundingDecimalField
from common.drf_custom.serializers import IdencodeModelSerializer
from rest_framework import serializers
from v2.transactions.models import ExternalTransaction


class AdminExternalTransactionModelSerializer(IdencodeModelSerializer):
    """Serializer class for admin external transaction list."""

    quantity = RoundingDecimalField(
        source="source_quantity",
        read_only=True,
        max_digits=100,
        decimal_places=2,
    )
    product_name = serializers.SerializerMethodField()
    source_name = serializers.SerializerMethodField()
    destination_name = serializers.SerializerMethodField()
    explorer_url = serializers.URLField(read_only=True)

    class Meta:
        model = ExternalTransaction
        fields = [
            "id",
            "created_on",
            "number",
            "quantity",
            "source_name",
            "explorer_url",
            "destination_name",
            "product_name",
            "blockchain_address",
            "date",
        ]

    @staticmethod
    def get_product_name(instance):
        """Returns product_name."""
        return instance.product.name

    @staticmethod
    def get_source_name(instance):
        """Returns source_name."""
        return instance.source.full_name

    @staticmethod
    def get_destination_name(instance):
        """Returns destination_name."""
        return instance.destination.full_name
