from common.drf_custom import fields as custom_fields
from sentry_sdk import capture_message
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction as django_transaction
from rest_framework import serializers
from v2.claims import constants
from v2.claims.models import FieldResponse
from v2.claims.models import TransactionClaim, GuardianClaim
from v2.claims.serializers import product_claims
from v2.claims.serializers.claims import ClaimVerifier
from v2.claims.serializers.claims import CriterionFieldResponseSerializer
from v2.guardian.tasks import initiate_guardian_claim
from v2.transactions.models import Transaction


class AttachClaimSerializer(serializers.Serializer):
    """Serializer to attach claim to a transaction A claims is attached to a
    batch by nature, it can be done at the time of creating a transaction, in
    such cases, the claims is attached to all the resulting batches and the
    claims data is also added to all the batches.

    A reference is also kept to know that the claim was added while
    doing the transaction.
    """

    id = custom_fields.IdencodeField(read_only=True)
    transaction = custom_fields.IdencodeField(related_model=Transaction)
    claims = ClaimVerifier(many=True)

    class Meta:
        fields = ("id", "transaction", "claims")
    
    def _initiate_guardian_claim(self, transaction_claim):
        if transaction_claim.claim.claim_processor == constants.GUARDIAN:
            transaction = transaction_claim.transaction
            batch = transaction.result_batches.first()
            att_claim = batch.claims.filter(
                claim=transaction_claim.claim
            ).first()
            att_claim.status = constants.STATUS_PENDING
            att_claim.save()
            guardian_claim = GuardianClaim.objects.create(
                trans_claim=att_claim
            )
            
            if not (
                transaction.source.has_valid_hedera_wallet() and
                transaction.destination.has_valid_hedera_wallet()
            ):
                return

            initiate_guardian_claim.delay(
                transaction.idencode, 
                transaction_claim.claim.idencode, 
                guardian_claim.idencode
            )
        return

    @django_transaction.atomic
    def create(self, validated_data):
        """Create overridden."""
        transaction = validated_data["transaction"]
        claim_batches = transaction.result_batches.all()
        for claim in validated_data["claims"]:
            attached_from = (
                constants.ATTACHED_BY_INHERITANCE
                if claim["inherited"]
                else constants.ATTACHED_FROM_TRANSACTION
            )
            for batch in claim_batches:
                batch_claim_data = {
                    "attached_from": attached_from,
                    "batch": batch,
                    "claim": claim["claim"],
                    "inherited": claim["inherited"],
                    "verifier": claim["verifier"],
                }
                batch_claims_serializer = product_claims.BatchClaimSerializer(
                    data=batch_claim_data, context=self.context
                )
                if not batch_claims_serializer.is_valid():
                    raise serializers.ValidationError(
                        batch_claims_serializer.errors
                    )
                batch_claims_serializer.save()
            transaction_claim = TransactionClaim.objects.create(
                transaction=validated_data["transaction"],
                claim=claim["claim"],
                verifier=claim["verifier"],
            )
            transaction_claim.log_activity()

            if transaction.source.is_farm:
                self._initiate_guardian_claim(transaction_claim)

        transaction.update_cache()

        return {"status": True, "message": "Claims Attached"}

    def to_representation(self, response):
        """Representing value."""
        return response


class TransactionCriterionFieldResponseSerializer(
    CriterionFieldResponseSerializer
):
    """Serializer to add criterion field responses to all batches in the
    transaction."""

    transaction = custom_fields.IdencodeField(
        related_model=Transaction, write_only=True
    )

    class Meta:
        model = FieldResponse
        fields = CriterionFieldResponseSerializer.Meta.fields + (
            "transaction",
        )

    def validate(self, attrs):
        """Validations."""
        field = attrs["field"]
        attrs = super(
            TransactionCriterionFieldResponseSerializer, self
        ).validate(attrs)
        transaction = attrs["transaction"]
        batches = transaction.result_batches.all()
        criteria = []
        for batch in batches:
            try:
                criterion = field.criterion.attached_criteria.get(
                    attachedbatchcriterion__batch_claim__batch=batch
                )
            except ObjectDoesNotExist:
                raise serializers.ValidationError("Invalid Transaction")
            criteria.append(criterion)
        attrs["criteria"] = criteria
        return attrs

    def create(self, validated_data):
        """Create overridden."""
        transaction = validated_data.pop("transaction")
        data = super(TransactionCriterionFieldResponseSerializer, self).create(
            validated_data
        )
        transaction.update_cache()
        return data
