"""Serializers for claim request related APIs."""
from common import library as common_lib
from common.drf_custom import fields as custom_fields
from common.exceptions import BadRequest
from django.core.files.base import ContentFile
from django.db import transaction as django_transaction
from rest_framework import serializers
from v2.claims import constants as claim_constants
from v2.claims.models import Claim
from v2.claims.serializers.claims import ClaimBasicSerializer
from v2.claims.serializers.company_claims import AttachCompanyClaimSerializer
from v2.claims.serializers.company_claims import (
    NodeCriterionFieldResponseSerializer,
)
from v2.supply_chains.models import Connection
from v2.supply_chains.models import Node
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.transparency_request import constants
from v2.transparency_request.models import ClaimRequest
from v2.transparency_request.models import ClaimRequestField


class ClaimRequestFieldSerializer(serializers.ModelSerializer):
    """Serializer for creating and retrieving response details."""

    id = custom_fields.IdencodeField(read_only=True)
    type = serializers.IntegerField(source="field.type", read_only=True)
    title = serializers.CharField(source="field.title", read_only=True)
    description = serializers.CharField(
        source="field.description", read_only=True
    )
    options = serializers.ListField(source="field.get_options", read_only=True)
    multiple_options = serializers.BooleanField(
        source="field.multiple_options", read_only=True
    )
    claim_request = custom_fields.IdencodeField()
    response = serializers.CharField(required=False)
    file = serializers.FileField(required=False)

    class Meta:
        model = ClaimRequestField
        fields = (
            "id",
            "type",
            "title",
            "description",
            "options",
            "multiple_options",
            "claim_request",
            "response",
            "file",
            "creator",
            "created_on",
        )

    def to_representation(self, instance):
        """Representation of data."""
        data = super(ClaimRequestFieldSerializer, self).to_representation(
            instance
        )
        data["request"] = {
            "id": instance.claim_request.idencode,
            "status": instance.claim_request.status,
            "note": instance.claim_request.note,
            "requester": instance.claim_request.requester.idencode,
            "requestee": instance.claim_request.requestee.idencode,
            "claim": instance.claim_request.claim.idencode,
        }
        return data


class ClaimRequestSerializer(serializers.ModelSerializer):
    """Serializer for creating.

    retrieving and updating claim requests
    """

    id = custom_fields.IdencodeField(read_only=True)
    number = serializers.IntegerField(read_only=True)
    status = serializers.IntegerField(required=False)
    request_type = serializers.IntegerField(read_only=True)
    node = custom_fields.IdencodeField(
        related_model=Node, source="requestee", write_only=True
    )
    requester = custom_fields.IdencodeField(
        serializer=NodeBasicSerializer, read_only=True
    )
    requestee = custom_fields.IdencodeField(
        serializer=NodeBasicSerializer, read_only=True
    )
    claim = custom_fields.IdencodeField(
        related_model=Claim, serializer=ClaimBasicSerializer
    )
    fields = custom_fields.ManyToManyIdencodeField(
        serializer=ClaimRequestFieldSerializer, read_only=True
    )
    supply_chain = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = ClaimRequest
        fields = (
            "id",
            "number",
            "status",
            "request_type",
            "node",
            "claim",
            "note",
            "created_on",
            "requester",
            "requestee",
            "fields",
            "response",
            "updated_on",
            "claim_attached",
            "supply_chain",
        )

    @django_transaction.atomic
    def attach_claim_from_request(self, claim_request):
        """Attach claim from request."""
        if claim_request.claim.scope != claim_constants.CLAIM_SCOPE_LOCAL:
            raise BadRequest(
                "Only Private claims can be added through this API"
            )
        if not all([field.responded for field in claim_request.fields.all()]):
            raise BadRequest("Not all files are attached")
        for critetion in claim_request.claim.criteria.all():
            for field in critetion.fields.all():
                if not claim_request.fields.filter(field=field).exists():
                    raise BadRequest(
                        "Claims seems to have changed. Please contact admin"
                    )
        attach_claim_serializer = AttachCompanyClaimSerializer(
            data={
                "node": claim_request.requestee,
                "claims": [claim_request.claim.idencode],
                "override": True,
            },
            context=self.context,
        )
        if not attach_claim_serializer.is_valid():
            raise serializers.ValidationError(attach_claim_serializer.errors)
        attached_company_claim = attach_claim_serializer.save()
        for field in claim_request.fields.all():
            field_data = {
                "node": claim_request.requestee,
                "field": field.field,
                "response": field.response,
            }
            if field.file:
                new_file = ContentFile(field.file.read())
                new_file.name = field.file.name
                field_data["file"] = new_file
            field_response_serializer = NodeCriterionFieldResponseSerializer(
                data=field_data, context=self.context
            )
            if not field_response_serializer.is_valid():
                raise serializers.ValidationError(
                    field_response_serializer.errors
                )
            field_response_serializer.save()
            claim_request.status = (
                constants.TRANSPARENCY_REQUEST_STATUS_COMPLETED
            )
            claim_request.save()
        return attached_company_claim

    def validate_claim(self, claim):
        """Validate claim."""
        current_node = self.context["view"].kwargs["node"]
        if claim.type == claim_constants.CLAIM_TYPE_PRODUCT:
            raise serializers.ValidationError(
                "Cannot attach product claim to company"
            )
        if claim.scope == claim_constants.CLAIM_SCOPE_LOCAL:
            if current_node not in claim.owners.all():
                raise serializers.ValidationError(
                    f"{current_node.full_name} is not permitted to use"
                    f" {claim.name} claim"
                )
        return claim

    def create(self, validated_data):
        """Overridden create."""
        current_node = self.context["view"].kwargs["node"]
        validated_data["requester"] = current_node
        supply_chain = validated_data.pop("supply_chain", None)
        claim_request = super(ClaimRequestSerializer, self).create(
            validated_data
        )
        claim_request.log_activity()
        claim_request.notify()
        connection = Connection.objects.filter(
            buyer=validated_data["requester"],
            supplier=validated_data["requestee"],
            supply_chain_id=common_lib._decode(supply_chain),
        ).first()
        if connection:
            connection.update_graph_node()

        if claim_request.claim.scope == claim_constants.CLAIM_SCOPE_LOCAL:
            for critetion in validated_data["claim"].criteria.all():
                for field in critetion.fields.all():
                    ClaimRequestField.objects.create(
                        claim_request=claim_request, field=field
                    )
        return claim_request

    def update(self, instance, validated_data):
        """Overridden update()."""
        current_node = self.context["view"].kwargs["node"]
        if instance.status in [
            constants.TRANSPARENCY_REQUEST_STATUS_COMPLETED,
            constants.TRANSPARENCY_REQUEST_STATUS_DECLINED,
        ]:
            raise BadRequest(
                "Status cannot be changed for already Completed/Declined"
                " requests"
            )
        if (
            validated_data["status"]
            == constants.TRANSPARENCY_REQUEST_STATUS_DECLINED
        ):
            if current_node == instance.requestee:
                instance.reject(validated_data["response"])
                # Send notification only when requestee rejects a request
            else:
                instance.status = (
                    constants.TRANSPARENCY_REQUEST_STATUS_DECLINED
                )
            instance.save()
        elif instance.claim.scope == claim_constants.CLAIM_SCOPE_LOCAL:
            if validated_data["status"] in [
                constants.TRANSPARENCY_REQUEST_STATUS_ACKNOWLEDGED,
            ]:
                instance.status = validated_data["status"]
                instance.notify_response()
                instance.save()
        else:
            raise BadRequest(
                "Status can only be changed to Declined/Acknowledged"
            )
        return instance
