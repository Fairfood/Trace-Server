"""Serializers for claims related APIs."""
from common.drf_custom import fields as custom_fields
from common.exceptions import BadRequest
from rest_framework import serializers
from v2.claims import constants
from v2.claims.models import AttachedBatchClaim
from v2.claims.models import AttachedClaim
from v2.claims.models import ClaimComment
from v2.products.serializers import batch as batch_serializers
from v2.products.serializers import product as prod_serializers
from v2.supply_chains.models import Node
from v2.supply_chains.serializers import node as node_serializers
from v2.transactions.serializers.other import TransactionSerializer

from .claims import AttachedCriterionSerializer
from .claims import ClaimBasicSerializer

"""Serializers for claims related APIs."""


# from v2.supply_chains.serializers.public import NodeBasicSerializer


class VerificationListSerializer(serializers.ModelSerializer):
    """Serializer to get details of batch claims for a verifier."""

    id = custom_fields.IdencodeField(read_only=True)
    status = serializers.IntegerField(read_only=True)
    batch_number = serializers.IntegerField(
        source="attachedbatchclaim.batch.number"
    )
    claim = custom_fields.IdencodeField(
        serializer=ClaimBasicSerializer, read_only=True
    )
    product = custom_fields.IdencodeField(
        serializer=prod_serializers.ProductSerializer,
        source="attachedbatchclaim.batch.product",
        read_only=True,
    )
    node = custom_fields.IdencodeField(
        read_only=True,
        serializer=node_serializers.NodeListSerializer,
        source="attachedcompanyclaim.node",
    )
    attached_by = custom_fields.IdencodeField(
        read_only=True, serializer=node_serializers.NodeListSerializer
    )
    verifier = custom_fields.IdencodeField(
        read_only=True, serializer=node_serializers.NodeListSerializer
    )

    class Meta:
        model = AttachedBatchClaim
        fields = (
            "id",
            "claim",
            "status",
            "batch_number",
            "product",
            "attached_by",
            "verifier",
            "node",
        )


class CommentSerializer(serializers.ModelSerializer):
    """Serializer to add comments to verifications."""

    id = custom_fields.IdencodeField(read_only=True)
    node = custom_fields.KWArgsObjectField(
        related_model=Node, source="sender", write_only=True
    )
    sender = custom_fields.IdencodeField(
        serializer=node_serializers.NodeListSerializer, read_only=True
    )
    verification = custom_fields.IdencodeField(
        related_model=AttachedClaim,
        source="attached_claim",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ClaimComment
        fields = (
            "id",
            "node",
            "sender",
            "verification",
            "message",
            "created_on",
        )

    def create(self, validated_data):
        """To perform function create."""
        comment = super(CommentSerializer, self).create(validated_data)
        comment.log_activity()
        return comment


class VerificationSerializer(serializers.ModelSerializer):
    """Serializer to verify batch claims."""

    id = custom_fields.IdencodeField(read_only=True)
    status = serializers.IntegerField()
    claim = custom_fields.IdencodeField(
        serializer=ClaimBasicSerializer, read_only=True
    )
    batch = custom_fields.IdencodeField(
        serializer=batch_serializers.BatchBasicSerializer,
        read_only=True,
        source="attachedbatchclaim.batch",
    )
    product = custom_fields.IdencodeField(
        serializer=prod_serializers.ProductSerializer,
        read_only=True,
        source="attachedbatchclaim.batch.product",
    )
    node = custom_fields.IdencodeField(
        serializer=node_serializers.NodeListSerializer,
        read_only=True,
        source="attachedcompanyclaim.node",
    )
    attached_by = custom_fields.IdencodeField(
        read_only=True, serializer=node_serializers.NodeListSerializer
    )
    verifier = custom_fields.IdencodeField(
        read_only=True, serializer=node_serializers.NodeListSerializer
    )
    transaction = custom_fields.IdencodeField(
        serializer=TransactionSerializer,
        read_only=True,
        source="attachedbatchclaim.transaction",
    )
    criteria = custom_fields.ManyToManyIdencodeField(
        serializer=AttachedCriterionSerializer,
        read_only=True,
        source="claim_object.criteria",
    )
    comments = custom_fields.ManyToManyIdencodeField(
        serializer=CommentSerializer, read_only=True
    )
    verifiable = serializers.SerializerMethodField(
        "is_verifiable", read_only=True
    )
    view_transaction = serializers.SerializerMethodField(
        "can_view_transaction", read_only=True
    )

    class Meta:
        model = AttachedClaim
        fields = (
            "id",
            "claim",
            "status",
            "batch",
            "product",
            "attached_by",
            "transaction",
            "criteria",
            "note",
            "comments",
            "node",
            "verifier",
            "verifiable",
            "view_transaction",
        )

    def is_verifiable(self, instance):
        """To perform function is_verifiable."""
        current_node = self.context["view"].kwargs["node"]
        if instance.verifier != current_node:
            return False
        if instance.status in [
            constants.STATUS_APPROVED,
            constants.STATUS_REJECTED,
        ]:
            return False
        return True

    def can_view_transaction(self, instance):
        """To perform function can_view_transaction."""
        current_node = self.context["view"].kwargs["node"]
        if instance.claim.type == constants.CLAIM_TYPE_PRODUCT:
            if hasattr(instance, "attachedbatchclaim"):
                if instance.attachedbatchclaim.batch.node == current_node:
                    return True
                if (
                    instance.attachedbatchclaim.batch.source_transaction.source
                    == current_node
                ):
                    return True
        return False

    def update(self, instance, validated_data):
        """To perform function update."""
        current_node = self.context["view"].kwargs["node"]
        if current_node != instance.verifier:
            raise BadRequest("Only the verifier can update the status")
        if instance.status in [
            constants.STATUS_APPROVED,
            constants.STATUS_REJECTED,
        ]:
            raise BadRequest(
                "Status cannot be changed for already approved/rejected"
                " verifications"
            )
        if "status" in validated_data:
            if validated_data["status"] in [
                constants.STATUS_PENDING,
                constants.STATUS_PARTIAL,
            ]:
                raise BadRequest(
                    "Status can only be changed to approved or rejected"
                )
        data = super(VerificationSerializer, self).update(
            instance, validated_data
        )
        if data.claim.type == constants.CLAIM_TYPE_PRODUCT:
            (
                data.claim_object.batch.source_transaction.invalidate_cache()
                if data.claim_object
                else None
            )
        instance.verify()
        instance.log_verification_activity()
        instance.notify_verification()
        return data
