from common.drf_custom import fields as custom_fields
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction as django_transaction
from rest_framework import serializers
from v2.claims import constants
from v2.claims.models import AttachedCompanyClaim, GuardianClaim
from v2.claims.models import AttachedCompanyCriterion
from v2.claims.models import Claim
from v2.claims.models import FieldResponse
from v2.claims.serializers.claims import AttachedClaimSerializer
from v2.claims.serializers.claims import AttachedCriterionSerializer
from v2.claims.serializers.claims import CriterionFieldResponseSerializer
from v2.claims.serializers.product_claims import GuardianClaimSerializer
from v2.supply_chains.models import Node
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.transparency_request.models import ClaimRequest
from v2.guardian.tasks import initiate_guardian_claim

class NodeCriterionFieldResponseSerializer(CriterionFieldResponseSerializer):
    """To Add field response for company claims."""

    node = custom_fields.IdencodeField(related_model=Node, write_only=True)

    class Meta:
        model = FieldResponse
        fields = CriterionFieldResponseSerializer.Meta.fields + ("node",)

    def validate(self, attrs):
        """To perform function validate."""
        field = attrs["field"]
        node = attrs.pop("node")
        attrs = super(NodeCriterionFieldResponseSerializer, self).validate(
            attrs
        )

        try:
            criterion = field.criterion.attached_criteria.get(
                attachedcompanycriterion__company_claim__node=node
            )
        except ObjectDoesNotExist:
            raise serializers.ValidationError("Invalid Company Claim")
        attrs["criteria"] = [criterion]
        return attrs


class CompanyClaimSerializer(AttachedClaimSerializer):
    """Serializer for company claims."""

    node = custom_fields.IdencodeField(
        related_model=Node, serializer=NodeBasicSerializer
    )
    attached_by = custom_fields.IdencodeField(
        related_model=Node, serializer=NodeBasicSerializer, required=False
    )
    criteria = custom_fields.ManyToManyIdencodeField(
        serializer=AttachedCriterionSerializer, read_only=True
    )
    override = serializers.BooleanField(
        default=False, required=False, write_only=True
    )
    guardian_claims = custom_fields.ManyToManyIdencodeField(
        serializer=GuardianClaimSerializer,
        related_model=GuardianClaim, 
        read_only=True
    )

    class Meta:
        model = AttachedCompanyClaim
        fields = AttachedClaimSerializer.Meta.fields + (
            "node",
            "attached_by",
            "criteria",
            "override",
            "note",
            "guardian_claims"
        )

    @django_transaction.atomic
    def create(self, validated_data):
        """To perform function create."""
        override = validated_data.pop("override", False)
        current_user = validated_data["updater"]
        node = validated_data.pop("node")
        claim = validated_data.pop("claim")

        current_node = self.context["view"].kwargs["node"]
        validated_data["creator"] = current_user
        validated_data["verifier"] = claim.verifiers.first()
        if override:
            AttachedCompanyClaim.objects.filter(
                node=node, claim=claim, attached_by=current_node
            ).delete()
        company_claim, created = AttachedCompanyClaim.objects.get_or_create(
            node=node, claim=claim, attached_by=current_node
        )
        if not created:
            return company_claim
        company_claim.creator = current_user
        company_claim.save()
        company_claim_serializer = CompanyClaimSerializer(
            company_claim,
            data=validated_data,
            partial=True,
            context=self.context,
        )
        if not company_claim_serializer.is_valid():
            raise serializers.ValidationError(company_claim_serializer.errors)
        company_claim_serializer.save()
        for criterion in claim.criteria.all():
            AttachedCompanyCriterion.objects.create(
                criterion=criterion,
                company_claim=company_claim,
                creator=current_user,
                updater=current_user,
            )
        company_claim.log_activity()
        company_claim.notify()
        company_claim.verify()

        if claim.scope == constants.CLAIM_SCOPE_GLOBAL:
            for claim_request in ClaimRequest.objects.filter(
                claim=claim, requestee=node
            ):
                claim_request.mark_as_complete()
        return company_claim


class AttachCompanyClaimSerializer(serializers.Serializer):
    """Serializer to attach company claims."""

    node = custom_fields.IdencodeField(related_model=Node)
    claims = custom_fields.ManyToManyIdencodeField(related_model=Claim)
    override = serializers.BooleanField(
        default=False, required=False, write_only=True
    )

    class Meta:
        fields = ("node", "claims", "override")

    def validate_claims(self, claims):
        """To perform function validate_claims."""
        current_node = self.context["view"].kwargs["node"]
        if not claims:
            raise serializers.ValidationError("No claims found.")
        for claim in claims:
            if claim.type == constants.CLAIM_TYPE_PRODUCT:
                raise serializers.ValidationError(
                    "Cannot attach product claim to company"
                )
            if claim.scope == constants.CLAIM_SCOPE_LOCAL:
                if current_node not in claim.owners.all():
                    raise serializers.ValidationError(
                        f"{current_node.full_name} is not permitted to use"
                        f" {claim.name} claim"
                    )
        return claims

    @django_transaction.atomic
    def create(self, validated_data):
        """To perform function create."""
        override = validated_data.pop("override", False)
        for claim in validated_data["claims"]:
            node = validated_data["node"]
            company_claim_data = {
                "node": node,
                "claim": claim,
                "verifier": claim.verifiers.first(),
                "override": override,
            }
            company_claims_serializer = CompanyClaimSerializer(
                data=company_claim_data, context=self.context
            )
            if not company_claims_serializer.is_valid():
                raise serializers.ValidationError(
                    company_claims_serializer.errors
                )
            company_claim = company_claims_serializer.save()

            if company_claim.claim.claim_processor == constants.GUARDIAN:
                company_claim.status = constants.STATUS_PENDING
                company_claim.save()
                guardian_claim = GuardianClaim.objects.create(
                    company_claim=company_claim
                )
                initiate_guardian_claim.delay(
                    node.idencode, 
                    claim.idencode, 
                    guardian_claim.idencode
                )

        return {"status": True, "message": "Claims Attached"}

    def to_representation(self, response):
        """To perform function to_representation."""
        return response
