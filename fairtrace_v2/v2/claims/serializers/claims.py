"""Serializers for claims related APIs."""
from common import library as common_lib
from common.drf_custom import fields as custom_fields
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction as django_transaction
from rest_framework import serializers
from v2.accounts.models import FairfoodUser
from v2.claims import constants
from v2.claims.models import AttachedClaim
from v2.claims.models import AttachedCriterion
from v2.claims.models import Claim
from v2.claims.models import Criterion
from v2.claims.models import CriterionField
from v2.claims.models import FieldResponse
from v2.products.models import Batch
from v2.products.models import Product
from v2.supply_chains.models import Node
from v2.supply_chains.serializers import supply_chain as sc_serializers
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.transparency_request.models import StockRequest


class CriterionFieldSerializer(serializers.ModelSerializer):
    """Serializer for claim criterion field."""

    id = custom_fields.IdencodeField()
    options = serializers.ListField(source="get_options")

    class Meta:
        model = CriterionField
        fields = (
            "id",
            "type",
            "title",
            "description",
            "multiple_options",
            "options",
        )


class FieldResponseSerializer(serializers.ModelSerializer):
    """Serializer for claim critetion field response."""

    field_id = serializers.CharField(source="field.idencode")
    options = serializers.ListField(source="field.get_options")
    type = serializers.IntegerField(source="field.type")
    title = serializers.CharField(source="field.title")
    description = serializers.CharField(source="field.description")
    multiple_options = serializers.BooleanField(
        source="field.multiple_options"
    )
    file = serializers.CharField(source="file_url")
    response = serializers.CharField()
    added_by = custom_fields.IdencodeField(
        related_model=Node, serializer=NodeBasicSerializer, required=False
    )

    class Meta:
        model = FieldResponse
        fields = (
            "field_id",
            "options",
            "type",
            "title",
            "description",
            "file",
            "multiple_options",
            "response",
            "added_by",
        )


class CriterionFieldResponseSerializer(serializers.ModelSerializer):
    """Serializer to add response for a criterion field."""

    id = custom_fields.IdencodeField(read_only=True)
    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True
    )
    field = custom_fields.IdencodeField(related_model=CriterionField)
    response = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False)
    added_by = custom_fields.IdencodeField(
        related_model=Node, serializer=NodeBasicSerializer, required=False
    )

    class Meta:
        model = FieldResponse
        fields = ("id", "user", "field", "response", "file", "added_by")

    def validate(self, attrs):
        """To perform function validate."""
        field = attrs["field"]
        if field.type == constants.FIELD_TYPE_FILE:
            if "file" not in attrs:
                raise serializers.ValidationError("File not attached.")
            attrs["file_hash"] = common_lib._hash_file(attrs["file"])
        if field.type == constants.FIELD_TYPE_TEXT:
            if "response" not in attrs:
                raise serializers.ValidationError("Response not supplied.")
        if field.type == constants.FIELD_TYPE_OPTION:
            if "response" not in attrs:
                raise serializers.ValidationError("Response not supplied.")
            if attrs["response"] not in field.get_options():
                raise serializers.ValidationError("Invalid option")
        return attrs

    @django_transaction.atomic
    def create(self, validated_data):
        """To perform function create."""
        criteria = validated_data.pop("criteria")
        current_node = self.context["view"].kwargs["node"]
        current_user = validated_data.pop("user")
        for criterion in criteria:
            try:
                field_response = FieldResponse.objects.get(
                    field=validated_data["field"], criterion=criterion
                )
                validated_data["updater"] = current_user
                if "file" in validated_data:
                    field_response.file = validated_data["file"]
                    field_response.file_hash = validated_data["file_hash"]
                if "response" in validated_data:
                    field_response.response = validated_data["response"]
                field_response.added_by = current_node
                field_response.save()
            except Exception:
                validated_data["criterion"] = criterion
                validated_data["added_by"] = current_node
                validated_data["creator"] = current_user
                validated_data["updater"] = current_user
                field_response = super(
                    CriterionFieldResponseSerializer, self
                ).create(validated_data)
        return {"status": True, "message": "Response recorded"}

    def to_representation(self, response):
        """To perform function to_representation."""
        return response


class CriterionSerializer(serializers.ModelSerializer):
    """Serializer to get criterion details."""

    id = custom_fields.IdencodeField()
    fields = custom_fields.ManyToManyIdencodeField(
        serializer=CriterionFieldSerializer, read_only=True
    )
    responses = custom_fields.ManyToManyIdencodeField(
        serializer=CriterionFieldResponseSerializer, write_only=True
    )
    context = serializers.JSONField(read_only=True)

    class Meta:
        model = Criterion
        exclude = (
            "created_on",
            "updated_on",
            "creator",
            "updater",
            "claim",
            "reference",
        )


class FFAdminVerifierSerializer(serializers.ModelSerializer):
    """Serializer Basic node details."""

    id = custom_fields.IdencodeField(read_only=True)
    name = serializers.CharField(source="full_name")

    class Meta:
        """Meta data."""

        model = Node
        fields = ("id", "name")


class ClaimSerializer(serializers.ModelSerializer):
    """Serializer to get claim details."""

    id = custom_fields.IdencodeField()
    criteria = custom_fields.ManyToManyIdencodeField(
        serializer=CriterionSerializer
    )
    supply_chains = custom_fields.ManyToManyIdencodeField(
        serializer=sc_serializers.SupplyChainSerializer,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    verifiers = custom_fields.ManyToManyIdencodeField(
        serializer=FFAdminVerifierSerializer, required=False
    )

    class Meta:
        model = Claim
        exclude = (
            "reference",
            "created_on",
            "updated_on",
            "creator",
            "updater",
        )


class ClaimBasicSerializer(serializers.ModelSerializer):
    """Basic claim serializer."""

    id = custom_fields.IdencodeField()

    class Meta:
        model = Claim
        fields = (
            "id",
            "type",
            "scope",
            "name",
            "description_basic",
            "description_full",
        )


class AttachedClaimSerializer(serializers.ModelSerializer):
    """Serializer to create batch claims."""

    user = custom_fields.KWArgsObjectField(write_only=True, source="updater")
    node = custom_fields.KWArgsObjectField(
        related_model=Node, source="attached_by", write_only=True
    )
    attached_from = serializers.IntegerField(
        required=False, default=constants.ATTACHED_DIRECTLY
    )
    claim = custom_fields.IdencodeField(related_model=Claim, write_only=True)

    id = custom_fields.IdencodeField(read_only=True)
    status = serializers.IntegerField(read_only=True)
    blockchain_address = serializers.CharField(read_only=True)
    claim_id = serializers.CharField(read_only=True, source="claim.idencode")
    name = serializers.CharField(read_only=True, source="claim.name")
    type = serializers.IntegerField(read_only=True, source="claim.type")
    scope = serializers.IntegerField(read_only=True, source="claim.scope")
    description_basic = serializers.CharField(
        read_only=True, source="claim.description_basic"
    )
    description_full = serializers.CharField(
        read_only=True, source="claim.description_full"
    )
    image = serializers.CharField(read_only=True, source="claim.image")
    verifier = custom_fields.IdencodeField(
        related_model=Node,
        serializer=NodeBasicSerializer,
        required=False,
        allow_null=True,
    )
    attached_by = custom_fields.IdencodeField(
        related_model=Node, serializer=NodeBasicSerializer, read_only=True
    )

    class Meta:
        model = AttachedClaim
        fields = (
            "id",
            "claim",
            "type",
            "scope",
            "verifier",
            "attached_from",
            "status",
            "blockchain_address",
            "user",
            "name",
            "image",
            "claim_id",
            "attached_by",
            "description_basic",
            "description_full",
            "verifier",
            "node",
        )


class ClaimVerifier(serializers.Serializer):
    """Serializer claim verifier data."""

    claim = custom_fields.IdencodeField(related_model=Claim)
    verifier = custom_fields.IdencodeField(
        related_model=Node, allow_null=True, required=False
    )
    inherited = serializers.BooleanField(default=False)

    class Meta:
        fields = "__all__"

    def validate(self, attrs):
        """To perform function validate."""
        if attrs["claim"].type != constants.CLAIM_TYPE_PRODUCT:
            raise serializers.ValidationError(
                "Only Product claims can be added to batch or transaction"
            )
        if not attrs["inherited"]:
            if attrs["claim"].verified_by == constants.VERIFIED_BY_THIRD_PARTY:
                if "verifier" not in attrs or not attrs["verifier"]:
                    raise serializers.ValidationError(
                        f"Verifier is required for claim {attrs['claim'].name}"
                    )
        if (
            "verifier" in attrs
            and attrs["verifier"]
            and not attrs["verifier"].is_company()
        ):
            raise serializers.ValidationError("Verifier should be a company")
        return attrs


class BatchQuantitySerializer(serializers.Serializer):
    """Serializer for validating source products in a transaction."""

    batch = custom_fields.IdencodeField(related_model=Batch)
    quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3
    )

    class Meta:
        fields = ("batch", "quantity")

    def validate(self, attrs):
        """To perform function validate."""
        if attrs["batch"].current_quantity < attrs["quantity"]:
            raise serializers.ValidationError(
                "Batch quantity mismatch for %s" % attrs["batch"].idencode
            )
        return attrs


class InheritableClaimsSerializer(serializers.Serializer):
    """Serializer to compute which all claims can be inherited.

    If two batches are merged, there are a few properties if a claim that
    decides if a claim can be inherited to the new batch.
    Inheritable     : If the claim property inheritable is set to false,
                      that claim won't be inherited irrespective of the other
                      properties
    Proportional    : If proportional is set to true, the claim can be
                      inherited even if not all of the source batches have the
                      particular claim as verified. A verification percentage
                      will be assigned to the claim depending on the quantity
                      used from the verified batch.
    Removable       : Decided whether is a claim is inherited, a user can
                      stop the claim from being inherited before doing the
                      transaction

    Further, if a transaction is created based on a transparency request,
    all the claims that are requested in the transparency request will
    automatically be selected and the user needs to upload the evidences if
    it is not inherited. It also cannot be removed.
    """

    batches = BatchQuantitySerializer(
        write_only=True, many=True, required=False
    )
    output_products = custom_fields.ManyToManyIdencodeField(
        related_model=Product
    )
    transparency_request = custom_fields.IdencodeField(
        related_model=StockRequest, required=False
    )

    class Meta:
        fields = ("batches", "output_products", "transparency_request")

    def validate_batches(self, batches):
        """To perform function validate_batches."""
        if not batches:
            raise serializers.ValidationError("Batches cannot be empty")
        return batches

    def create(self, validated_data):
        """To perform function create."""
        products = validated_data["output_products"]
        batches = validated_data["batches"]
        claims = {
            i.claim
            for i in batches[0]["batch"].claims.filter(
                status=constants.STATUS_APPROVED
            )
        }
        batch_prods = {batches[0]["batch"].product}
        for batch in batches[1:]:
            claims &= {
                i.claim
                for i in batch["batch"].claims.filter(
                    status=constants.STATUS_APPROVED
                )
            }
            batch_prods &= {batch["batch"].product}
        for batch in batches:
            claims |= {
                i.claim
                for i in batch["batch"].claims.filter(
                    status=constants.STATUS_APPROVED, claim__proportional=True
                )
            }
            # if INHERITANCE_TYPE_ALL in any of the batches, it will be
            # included.
            claims |= {
                i.claim
                for i in batch["batch"].claims.filter(
                    status=constants.STATUS_APPROVED,
                    claim__inheritable=constants.INHERITANCE_TYPE_ALL,
                )
            }
        common_claims = list(claims)

        if "transparency_request" in validated_data:
            trr_claims = validated_data["transparency_request"].claims.all()
        else:
            trr_claims = []
        inheritable_claims = []

        for claim in common_claims:
            if claim in trr_claims:
                removable = False
            else:
                removable = claim.removable
            claim_data = {
                "claim": claim.idencode,
                "removable": removable,
                "criteria": [],
            }
            inheritable = False
            if claim.inheritable == constants.INHERITANCE_TYPE_ALL:
                inheritable = True
            elif claim.inheritable == constants.INHERITANCE_TYPE_PRODUCT:
                inheritable = False
                if (
                    products.count() == len(batch_prods) == 1
                    and products.first() == list(batch_prods)[0]
                ):
                    inheritable = True
            if not inheritable:
                continue
            total = 0
            verified = 0
            batch_claim_data = []
            for batch_dict in batches:
                batch = batch_dict["batch"]
                quantity = batch_dict["quantity"]
                total += quantity
                try:
                    from v2.claims.serializers.product_claims import (
                        BatchClaimSerializer,
                    )

                    batch_claim = batch.claims.get(claim=claim)
                    batch_claim_data.append(
                        BatchClaimSerializer(batch_claim).data
                    )
                    verified += float(quantity) * (
                        batch_claim.verification_percentage / 100
                    )
                except ObjectDoesNotExist:
                    pass

            criteria_dict = {}
            for batch_data in batch_claim_data:
                # There was this if condition which prevented files from
                # inherited claims to be shown in the front-end. Removing
                # the condition to fix the bug FAIRFOOD-954

                for criteria in batch_data["criteria"]:
                    criterion_id = criteria["criterion_id"]
                    if criterion_id not in criteria_dict:
                        criteria_dict[criterion_id] = {}
                    for resp in criteria["field_responses"]:
                        added_by = resp.pop("added_by")
                        field_data = {
                            "batch": batch_data["batch"],
                            "field_response": resp,
                        }
                        if added_by["id"] not in criteria_dict[criterion_id]:
                            node_data = {
                                "added_by": added_by,
                                "responses": [field_data],
                            }
                            criteria_dict[criterion_id][
                                added_by["id"]
                            ] = node_data
                        else:
                            criteria_dict[criterion_id][added_by["id"]][
                                "responses"
                            ].append(field_data)
            for criterion_id, data_dict in criteria_dict.items():
                node_responses = []
                for node_id, response in data_dict.items():
                    node_responses.append(response)
                claim_data["criteria"].append(
                    {"id": criterion_id, "node_responses": node_responses}
                )
            claim_data["verification_percentage"] = common_lib._percentage(
                verified, total
            )
            inheritable_claims.append(claim_data)
        return inheritable_claims

    def to_representation(self, claims):
        """To perform function to_representation."""
        return {"inheritable_claims": claims}


class AttachedCriterionSerializer(serializers.ModelSerializer):
    """Serializer to get the details of the criterions attached to a batch."""

    criterion_id = serializers.CharField(source="criterion.idencode")
    name = serializers.CharField(read_only=True, source="criterion.name")
    verification_type = serializers.CharField(
        read_only=True, source="criterion.verification_type"
    )
    description = serializers.CharField(
        read_only=True, source="criterion.description"
    )
    context = serializers.JSONField(read_only=True, source="criterion.context")
    method = serializers.IntegerField(
        read_only=True, source="criterion.method"
    )
    evidences = serializers.JSONField(read_only=True, source="evidence")
    field_responses = custom_fields.ManyToManyIdencodeField(
        serializer=FieldResponseSerializer, read_only=True
    )

    class Meta:
        model = AttachedCriterion
        fields = (
            "criterion_id",
            "name",
            "description",
            "field_responses",
            "verification_type",
            "context",
            "method",
            "evidences",
        )
