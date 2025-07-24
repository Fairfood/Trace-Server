import requests
import json
from django.conf import settings
from common.drf_custom import fields as custom_fields
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction as django_transaction
from rest_framework import serializers
from common.drf_custom.fields import JsonField
from common.library import convert_to_timestamp
from v2.claims import constants
from v2.claims.models import (
    AttachedBatchClaim, AttachedCompanyClaim, GuardianClaim
)
from v2.claims.models import AttachedBatchCriterion
from v2.claims.models import FieldResponse
from v2.claims.serializers.claims import AttachedClaimSerializer
from v2.claims.serializers.claims import AttachedCriterionSerializer
from v2.claims.serializers.claims import ClaimVerifier
from v2.claims.serializers.claims import CriterionFieldResponseSerializer
from v2.products.models import Batch
from v2.products.serializers import product as prod_serializers


class BatchCriterionFieldResponseSerializer(CriterionFieldResponseSerializer):
    """Serializer to add field response to product claims."""

    batch = custom_fields.IdencodeField(related_model=Batch, write_only=True)

    class Meta:
        model = FieldResponse
        fields = CriterionFieldResponseSerializer.Meta.fields + ("batch",)

    def validate(self, attrs):
        """To perform function validate."""
        field = attrs["field"]
        batch = attrs["batch"]
        attrs = super(BatchCriterionFieldResponseSerializer, self).validate(
            attrs
        )

        try:
            criterion = field.criterion.attached_criteria.get(
                attachedbatchcriterion__batch_claim__batch=batch
            )
        except ObjectDoesNotExist:
            raise serializers.ValidationError("Invalid Batch")
        attrs["criteria"] = [criterion]
        return attrs

    def create(self, validated_data):
        """To perform function create."""
        batch = validated_data.pop("batch")
        data = super(BatchCriterionFieldResponseSerializer, self).create(
            validated_data
        )
        batch.source_transaction.update_cache()
        return data


class GuardianClaimSerializer(serializers.ModelSerializer):
    """Serializer for guardian claim"""

    id = custom_fields.IdencodeField(read_only=True)
    trans_claim = custom_fields.IdencodeField(
        related_model=AttachedBatchClaim, required=False
    )
    company_claim = custom_fields.IdencodeField(
        related_model=AttachedCompanyClaim, required=False
    )
    extra_info = JsonField()
    guardian_url = serializers.SerializerMethodField()
    hashscan_url = serializers.SerializerMethodField()

    class Meta:
        model = GuardianClaim
        fields = '__all__'
    
    def get_hashscan_url(self, obj):
        """
        Fetches the transaction ID related to a token claim by querying 
        HashScan.

        Since the transaction ID is not available in the extra_info, 
        this method retrieves transactions from HashScan based on the 
        token ID and identifies the relevant transaction associated with 
        the claim.
        """
        from v2.guardian import constants as guard_consts

        base_url = guard_consts.TESTNET_URL
        env = guard_consts.TESTNET
        if settings.ENVIRONMENT == 'production':
            base_url = guard_consts.MAINNET_URL
            env = guard_consts.MAINNET
        
        account_id = settings.GUARDIAN_SD_ACCOUNT_ID
       
        try:
            extra_info = obj.extra_info
            if not extra_info:
                return ""

            if isinstance(extra_info, str):
                extra_info = json.loads(extra_info)

            create_date = extra_info.get(
                "vpDocument", {}).get("document", {}).get("createDate")
            token_id = extra_info.get("mintDocument", {}).get("tokenId")

            if not create_date or not token_id:
                return ""

            timestamp = convert_to_timestamp(create_date)
            url = (
                f"{base_url}/api/v1/transactions"
                f"?limit=100&order=asc"
                f"&account.id={account_id}"
                f"&transactiontype=CRYPTOTRANSFER"
                f"&timestamp=gte:{timestamp}"
            )

            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            transactions = data.get("transactions", [])
            for txn in transactions:
                token_transfers = txn.get("token_transfers", [])
                for transfer in token_transfers:
                    if transfer.get("token_id") == token_id:
                        transaction_id = txn.get("transaction_id")
                        return (
                            f"https://hashscan.io/{env}/"
                            f"transaction/{transaction_id}"
                        )

            print("No matching token_id found in any transaction.")
            return ""
        except Exception as e:
            print(f"Unexpected error: {e}")
        return ""
     
    def get_guardian_url(self, obj):
        """return guardian url"""
        return settings.GUARDIAN_URL[:-6]


class BatchClaimSerializer(AttachedClaimSerializer):
    """Serializer for create BatchClaims."""

    batch = custom_fields.IdencodeField(related_model=Batch)
    criteria = custom_fields.ManyToManyIdencodeField(
        serializer=AttachedCriterionSerializer, read_only=True
    )
    product = custom_fields.IdencodeField(
        serializer=prod_serializers.ProductSerializer,
        source="batch.product",
        read_only=True,
    )
    guardian_claims = custom_fields.ManyToManyIdencodeField(
        serializer=GuardianClaimSerializer,
        related_model=GuardianClaim, 
        read_only=True
    )

    class Meta:
        model = AttachedBatchClaim
        fields = AttachedClaimSerializer.Meta.fields + (
            "batch",
            "criteria",
            "product",
            "verification_percentage",
            "guardian_claims"
        )

    @django_transaction.atomic
    def create(self, validated_data):
        """To perform function create."""
        current_user = validated_data["updater"]
        validated_data["creator"] = current_user
        batch = validated_data.pop("batch")
        claim = validated_data.pop("claim")
        current_node = self.context["view"].kwargs["node"]
        validated_data["attached_by"] = current_node
        if claim.verified_by == constants.VERIFIED_BY_SECOND_PARTY:
            validated_data["verifier"] = batch.node

        batch_claim, created = AttachedBatchClaim.objects.get_or_create(
            batch=batch, claim=claim
        )
        if not created:
            return batch_claim
        batch_claim.creator = current_user
        batch_claim.save()
        batch_claim_serializer = BatchClaimSerializer(
            batch_claim,
            data=validated_data,
            partial=True,
            context=self.context,
        )
        if not batch_claim_serializer.is_valid():
            raise serializers.ValidationError(batch_claim_serializer.errors)
        batch_claim_serializer.save()
        for criterion in claim.criteria.all():
            AttachedBatchCriterion.objects.create(
                criterion=criterion,
                batch_claim=batch_claim,
                attached_from=validated_data["attached_from"],
                creator=current_user,
                updater=current_user,
            )
        batch_claim.log_activity()
        if batch_claim.attached_from == constants.ATTACHED_BY_INHERITANCE:
            batch_claim.inherit_data()
        else:
            batch_claim.notify()
        batch_claim.verify()
        return batch_claim

    def update(self, instance, validated_data):
        """To perform function update."""
        if (
            validated_data["attached_from"]
            == constants.ATTACHED_BY_INHERITANCE
        ):
            validated_data.pop("attached_by")
        data = super(BatchClaimSerializer, self).update(
            instance, validated_data
        )

        return data


class AttachBatchClaimSerializer(serializers.Serializer):
    """Serializer to attach claim to batch."""

    batch = custom_fields.IdencodeField(related_model=Batch)
    claims = ClaimVerifier(many=True)

    class Meta:
        fields = ("batch", "claims")

    @django_transaction.atomic
    def create(self, validated_data):
        """To perform function create."""
        for claim in validated_data["claims"]:
            batch_claim_data = {
                "attached_from": constants.ATTACHED_DIRECTLY,
                "batch": validated_data["batch"],
                "claim": claim["claim"],
                "verifier": claim["verifier"],
            }
            batch_claims_serializer = BatchClaimSerializer(
                data=batch_claim_data, context=self.context
            )
            if not batch_claims_serializer.is_valid():
                raise serializers.ValidationError(
                    batch_claims_serializer.errors
                )
            batch_claims_serializer.save()
        return {"status": True, "message": "Claims Attached"}

    def to_representation(self, response):
        """To perform function to_representation."""
        return response
