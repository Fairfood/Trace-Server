"""Serializers for claims related APIs."""
from common.drf_custom import fields as custom_fields
from rest_framework import serializers
from v2.claims.models import Claim
from v2.claims.models import Criterion
from v2.claims.models import CriterionField
from v2.claims.serializers import claims as claims_serializers
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.serializers import supply_chain as sc_serializers


class CreateClaimSerializer(serializers.ModelSerializer):
    """Serializer to create claims."""

    id = custom_fields.IdencodeField(read_only=True)
    user = custom_fields.KWArgsObjectField(write_only=True, source="creator")
    supply_chains = custom_fields.ManyToManyIdencodeField(
        serializer=sc_serializers.SupplyChainSerializer,
        related_model=SupplyChain,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    verifiers = custom_fields.ManyToManyIdencodeField(
        serializer=claims_serializers.FFAdminVerifierSerializer, required=False
    )

    class Meta:
        model = Claim
        fields = (
            "id",
            "name",
            "description_basic",
            "description_full",
            "type",
            "scope",
            "proportional",
            "removable",
            "inheritable",
            "verified_by",
            "version",
            "active",
            "user",
            "supply_chains",
            "verifiers",
        )

    def validate_supply_chains(self, value):
        """To perform function validate_supply_chains."""
        if not value:
            return []
        return value


class CreateCriterionSerializer(serializers.ModelSerializer):
    """Serializer to create claim criteria."""

    id = custom_fields.IdencodeField(read_only=True)
    claim = custom_fields.IdencodeField(write_only=True)

    class Meta:
        model = Criterion
        fields = "__all__"


class CreateCriterionFieldSerializer(serializers.ModelSerializer):
    """Serializer to create criterion fields."""

    id = custom_fields.IdencodeField(read_only=True)
    criterion = custom_fields.IdencodeField(write_only=True)

    class Meta:
        model = CriterionField
        fields = "__all__"
