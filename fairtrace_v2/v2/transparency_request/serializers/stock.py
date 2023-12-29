"""Serializers for stock request related APIs."""
from common.drf_custom import fields as custom_fields
from common.exceptions import BadRequest
from rest_framework import serializers
from v2.claims import constants as claim_const
from v2.claims.models import AttachedBatchClaim
from v2.claims.models import Claim
from v2.claims.serializers.claims import ClaimBasicSerializer
from v2.products.models import Batch
from v2.products.models import Product
from v2.products.serializers.product import ProductSerializer
from v2.supply_chains.models import Connection
from v2.supply_chains.models import Node
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.transactions.serializers.external import (
    ExternalTransactionListSerializer,
)
from v2.transparency_request import constants
from v2.transparency_request.models import StockRequest


class StockRequestSerializer(serializers.ModelSerializer):
    """Serializer for creating and retrieving stock request details."""

    id = custom_fields.IdencodeField(read_only=True)
    number = serializers.IntegerField(read_only=True)
    status = serializers.IntegerField(required=False)

    node = custom_fields.KWArgsObjectField(
        related_model=Node, write_only=True, source="requester"
    )
    supplier = custom_fields.IdencodeField(
        related_model=Node, source="requestee", write_only=True
    )
    requester = custom_fields.IdencodeField(
        serializer=NodeBasicSerializer, read_only=True
    )
    requestee = custom_fields.IdencodeField(
        serializer=NodeBasicSerializer, read_only=True
    )
    product = custom_fields.IdencodeField(
        related_model=Product, serializer=ProductSerializer
    )
    claims = custom_fields.ManyToManyIdencodeField(
        related_model=Claim, serializer=ClaimBasicSerializer, required=False
    )

    class Meta:
        model = StockRequest
        fields = (
            "id",
            "number",
            "status",
            "node",
            "supplier",
            "product",
            "transaction",
            "claims",
            "quantity",
            "unit",
            "price",
            "note",
            "response",
            "currency",
            "created_on",
            "requester",
            "requestee",
            "request_type",
            "updated_on",
        )

    def validate(self, attrs):
        """To perform function validate."""
        if self.instance:
            if not self.instance.is_modifiable():
                raise serializers.ValidationError(
                    "Transparency request cannot be modified. It might be"
                    " completed."
                )

        return attrs

    def create(self, validated_data):
        """To perform function create."""
        try:
            validated_data["connection"] = Connection.objects.get(
                buyer=validated_data["requester"],
                supplier=validated_data["requestee"],
                supply_chain=validated_data["product"].supply_chain,
            )
        except Connection.DoesNotExist:
            raise BadRequest(
                "Node is not connected to"
                f" {validated_data['requestee'].full_name} in the"
                f" {validated_data['product'].supply_chain.name} supplychain."
            )
        stock_request = super(StockRequestSerializer, self).create(
            validated_data
        )
        stock_request.product.grant_access_to(stock_request.requestee)
        stock_request.log_activity()
        stock_request.notify()
        validated_data["connection"].update_graph_node()
        return stock_request

    def to_representation(self, instance):
        """To perform function to_representation."""
        data = super(StockRequestSerializer, self).to_representation(instance)
        data["transaction"] = ExternalTransactionListSerializer(
            instance.transaction, context=self.context
        ).data
        current_node = self.context["view"].kwargs["node"]
        if data["requester"]["id"] == current_node.idencode:
            data["node"] = data["requestee"]
        elif data["requestee"]["id"] == current_node.idencode:
            data["node"] = data["requester"]
        else:
            pass
        data.pop("requester")
        data.pop("requestee")
        return data

    def update(self, instance, validated_data):
        """To perform function update."""
        if instance.status in [
            constants.TRANSPARENCY_REQUEST_STATUS_COMPLETED,
            constants.TRANSPARENCY_REQUEST_STATUS_DECLINED,
        ]:
            raise BadRequest(
                "Status cannot be changed for already Completed/Declined"
                " requests"
            )
        current_node = self.context["view"].kwargs.get("node", None)
        for key in validated_data:
            if key == "status" or key == "requester" or key == "response":
                status = validated_data["status"]
            else:
                raise BadRequest(
                    "Not updated. You can only update status of your stock"
                    " request"
                )
        if status:
            if validated_data["status"] in [
                constants.TRANSPARENCY_REQUEST_STATUS_DECLINED,
            ]:
                if instance.requestee != current_node:
                    raise BadRequest(
                        "Only the receiver of the Stock request can reject it."
                    )
                instance.reject(validated_data["response"])
                instance.save()
            else:
                raise BadRequest("Status can only be changed to Declined")

        return instance


class StockRequestVerificationSerializer(serializers.Serializer):
    """Class to handle StockRequestVerificationSerializer and functions."""

    batches = custom_fields.ManyToManyIdencodeField(related_model=Batch)
    transparency_request = custom_fields.IdencodeField(
        related_model=StockRequest
    )

    class Meta:
        fields = ("batches", "transparency_request")

    def create(self, validated_data):
        """To perform function create."""
        batch_verification = []
        valid = True
        for batch in validated_data["batches"]:
            batch_valid = True
            claim_verification = []
            for claim in validated_data["transparency_request"].claims.all():
                claim_data = {
                    "claim": {"id": claim.id, "name": claim.name},
                    "valid": True,
                }
                if not AttachedBatchClaim.objects.filter(
                    batch=batch,
                    claim=claim,
                    status=claim_const.STATUS_APPROVED,
                ).exists():
                    claim_data["valid"] = False
                    batch_valid = False
                    valid = False
                claim_verification.append(claim_data)

            batch_data = {
                "id": batch.idencode,
                "number": batch.number,
                "claims": claim_verification,
                "valid": batch_valid,
            }
            batch_verification.append(batch_data)
        verification_data = {"valid": valid, "batches": batch_verification}
        return verification_data

    def to_representation(self, data):
        """To perform function to_representation."""
        return data
