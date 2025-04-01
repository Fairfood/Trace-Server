"""Serializers for products related APIs."""
from common.drf_custom import fields as custom_fields
from common.drf_custom.fields import IdencodeField
from common.drf_custom.serializers import IdencodeModelSerializer
from common.exceptions import AccessForbidden, BadRequest
from common.library import is_valid_gtin
from django.conf import settings
from rest_framework import serializers
from v2.claims.serializers import product_claims
from v2.dashboard.models import CITheme
from v2.products.models import Batch
from v2.products.models import BatchFarmerMapping
from v2.products.models import BatchMigration
from v2.products.serializers import product as prod_serializers
from v2.supply_chains.serializers.node import FarmerSerializer
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.supply_chains.serializers.public import NodeWalletSerializer
from v2.transactions.models import SourceBatch


# from v2.products.models import BatchComment


class BatchBasicSerializer(serializers.ModelSerializer):
    """Basic details of the batch that are available globally."""

    id = custom_fields.IdencodeField()
    product = custom_fields.IdencodeField(
        serializer=prod_serializers.ProductSerializer
    )

    class Meta:
        model = Batch
        fields = ("id", "product", "number", "unit", "initial_quantity")


class SourceBatchSerializer(serializers.Serializer):
    """Serializer for validating source products in a transaction."""

    batch = custom_fields.IdencodeField(
        related_model=Batch, serializer=BatchBasicSerializer
    )
    quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3
    )

    class Meta:
        model = SourceBatch
        fields = ("batch", "quantity")

    def validate(self, attrs):
        """validate datat."""
        if attrs["batch"].current_quantity < attrs["quantity"]:
            raise serializers.ValidationError(
                f"Batch quantity mismatch for  {attrs['batch'].idencode}."
                f" {attrs['quantity']} should be less than or equal to "
                f"current quantity {attrs['batch'].current_quantity}")
        return attrs


class AppSourceBatchSerializer(serializers.Serializer):
    """Serializer for validating source products in a transaction."""

    batch = custom_fields.IdencodeField(
        related_model=Batch, serializer=BatchBasicSerializer
    )
    quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3
    )

    class Meta:
        model = SourceBatch
        fields = ("batch", "quantity")


# class BatchCommentSerializer(serializers.ModelSerializer):
#     """ Serializer for batch comments """
#
#     id = custom_fields.IdencodeField(read_only=True)
#     batch = custom_fields.IdencodeField(related_model=Batch)
#
#     class Meta:
#         model = BatchComment
#         fields = '__all__'


class BatchSerializer(serializers.ModelSerializer):
    """Serializer for batch."""

    id = custom_fields.IdencodeField(read_only=True)
    product = custom_fields.IdencodeField(
        serializer=prod_serializers.ProductSerializer
    )
    node = custom_fields.IdencodeField()
    supplier = custom_fields.IdencodeField(
        read_only=True, source="sourced_from", serializer=NodeBasicSerializer
    )
    created_from = serializers.CharField(read_only=True, source="sourced_by")
    source_transaction = custom_fields.IdencodeField(read_only=True)
    created_on = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = (
            "id",
            "product",
            "node",
            "number",
            "name",
            "initial_quantity",
            "current_quantity",
            "unit",
            "verified_percentage",
            "created_on",
            "supplier",
            "created_from",
            "buyer_ref_number",
            "seller_ref_number",
            "external_source",
            "source_transaction",
            "archived"
        )

    def get_created_on(self, instance):
        """Get created on as transaction date."""
        return int(instance.source_transaction.created_on.timestamp())


class BatchMigrationSerializer(serializers.ModelSerializer):
    """Serializer for batch migrations."""

    id = custom_fields.IdencodeField(read_only=True)

    class Meta:
        model = BatchMigration
        fields = (
            "id",
            "wallet_type",
            "blockchain_hash",
            "info_display",
            "explorer_url",
            "prev_wallet_type",
            "prev_blockchain_hash",
            "prev_explorer_url",
        )


class BatchDetailSerializer(serializers.ModelSerializer):
    """Serializer for batch."""

    id = custom_fields.IdencodeField(read_only=True)
    product = custom_fields.IdencodeField(
        serializer=prod_serializers.ProductSerializer
    )
    node = custom_fields.IdencodeField()
    supplier = custom_fields.IdencodeField(
        read_only=True, source="sourced_from", serializer=NodeBasicSerializer
    )
    supplier_wallet = custom_fields.IdencodeField(
        read_only=True, source="source_wallet", serializer=NodeWalletSerializer
    )
    created_from = serializers.CharField(read_only=True, source="sourced_by")
    # comments = custom_fields.ManyToManyIdencodeField(
    #     serializer=BatchCommentSerializer)
    source_batches = custom_fields.ManyToManyIdencodeField(
        serializer=SourceBatchSerializer,
        source="source_transaction.source_batch_objects",
    )
    source_type = serializers.IntegerField(
        read_only=True, source="get_source_type"
    )
    source_transaction = serializers.SerializerMethodField(
        "get_source_transaction_details"
    )
    outgoing_transactions = serializers.SerializerMethodField(
        "get_outgoing_transactions"
    )
    claims = custom_fields.ManyToManyIdencodeField(
        serializer=product_claims.BatchClaimSerializer, read_only=True
    )
    migrations = custom_fields.ManyToManyIdencodeField(
        serializer=BatchMigrationSerializer, read_only=True
    )
    gtin = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Batch
        fields = (
            "id",
            "product",
            "node",
            "number",
            "name",
            "initial_quantity",
            "current_quantity",
            "unit",
            "verified_percentage",
            "claims",
            "created_on",
            "supplier",
            "supplier_wallet",
            "created_from",
            "note",
            "source_type",
            "source_batches",
            "source_transaction",
            "outgoing_transactions",
            "blockchain_hash",
            "explorer_url",
            "wallet_type",
            "migrations",
            "buyer_ref_number",
            "seller_ref_number",
            "gtin"
        )
    
    def validate(self, attrs):
        if "gtin" in attrs and attrs["gtin"]:
            if not is_valid_gtin(attrs["gtin"]):
                raise BadRequest("Invalid GTIN", send_to_sentry=False)
        return super().validate(attrs)

    def get_outgoing_transactions(self, instance):
        """Add details of outgoing transactions from the batch."""
        outgoing_transactions = []
        for (
            og_transaction
        ) in instance.outgoing_transaction_objects.all().order_by(
            "created_on"
        ):
            data = {
                "id": og_transaction.transaction.idencode,
                "type": og_transaction.transaction.transaction_type,
                "number": og_transaction.transaction.number,
                "date": int(og_transaction.transaction.created_on.timestamp()),
                "quantity": og_transaction.quantity,
            }
            outgoing_transactions.append(data)
        return outgoing_transactions

    def get_source_transaction_details(self, instance):
        """Get source transaction details."""
        source_transaction = instance.source_transaction
        details = {
            "id": source_transaction.idencode,
            "number": source_transaction.number,
            "blockchain_address": source_transaction.blockchain_address,
            "info_message_address": source_transaction.info_message_address,
            "type": instance.sourced_by,
            "transaction_type": source_transaction.transaction_type,
            "wallet_type": source_transaction.wallet_type,
            "explorer_url": source_transaction.explorer_url,
            "info_explorer_url": source_transaction.info_explorer_url,
            "date": int(source_transaction.date.timestamp()),
        }
        return details

    def to_representation(self, instance):
        """The representation value."""
        try:
            node = self.context["view"].kwargs["node"]
        except Exception:
            node = self.context["node"]
        if instance.node != node:
            raise AccessForbidden("Node does not have access to the batch")
        data = super(BatchDetailSerializer, self).to_representation(instance)
        nsc = instance.sourced_from.nodesupplychain_set.filter(
            supply_chain=instance.product.supply_chain
        ).first()
        primary_operation = {"id": "", "name": ""}
        if nsc.primary_operation:
            primary_operation = {
                "id": nsc.primary_operation.idencode,
                "name": nsc.primary_operation.name,
            }
        data["supplier"]["primary_operation"] = primary_operation
        data["consumer_interface_url"] = self._get_consumer_interface_url(
            node, instance
        )
        return data

    @staticmethod
    def _get_consumer_interface_url(node, instance):
        """To perform function _get_consumer_interface_url."""
        theme = CITheme.objects.filter(node=node).first()
        if not theme:
            theme = CITheme.objects.filter(is_public=True).first()
        if theme.version != "0" and settings.CONSUMER_INTERFACE_V2_URL:
            url = settings.CONSUMER_INTERFACE_V2_URL
            if instance.gtin:
                url = (
                    url[:-2] +
                    f"01/{instance.gtin}/10/{instance.idencode}?"
                    f"theme={theme.idencode}"
                )
            return url
        return ""


class AppBatchSerializer(serializers.ModelSerializer):
    """Serializer for batch."""

    id = custom_fields.IdencodeField(read_only=True)
    supplier = custom_fields.IdencodeField(
        read_only=True, source="sourced_from", serializer=NodeBasicSerializer
    )
    created_from = serializers.CharField(read_only=True, source="sourced_by")

    class Meta:
        model = Batch
        fields = (
            "id",
            "number",
            "name",
            "initial_quantity",
            "current_quantity",
            "unit",
            "verified_percentage",
            "created_on",
            "supplier",
            "created_from",
        )


class BatchFarmerMappingSerializer(IdencodeModelSerializer):
    """Serializer for the BatchFarmerMapping model.

    This serializer is used to convert BatchFarmerMapping instances to a
    serialized representation and vice versa. It inherits from the
    IdencodeModelSerializer, which includes ID encryption and decryption
    functionality.

    Fields:
    - farmer: Serialized representation of the associated Farmer instance.

    Meta:
    - model: The BatchFarmerMapping model.
    - fields: Special value "__all__" to include all fields from the model.
    """

    farmer = IdencodeField(serializer=FarmerSerializer, read_only=True)

    class Meta:
        model = BatchFarmerMapping
        fields = "__all__"
