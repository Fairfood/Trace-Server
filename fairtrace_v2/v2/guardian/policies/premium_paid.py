import requests
from sentry_sdk import capture_message
from django.db import transaction
from common.library import decode
from v2.claims.constants import STATUS_APPROVED, STATUS_PENDING
from v2.claims.models import GuardianClaim
from v2.transactions.models import ExternalTransaction
from v2.guardian import policy_const
from v2.guardian import constants as guard_const
from v2.guardian.policies.base import GuardianPolicyBase
from v2.guardian import tasks as guardian_tasks


class PremiumPaidPolicy(GuardianPolicyBase):
    """Concrete class for Premium Paid policy."""

    def build_submission_data(self, transaction: ExternalTransaction) -> dict:
        """Build data specific to premium paid policy."""
        evidence_type, evidence_hash = self.get_evidence_file_hash(
            transaction
        )
        data = {
            "document": {
                "transaction_id": transaction.idencode,
                "number": transaction.number,
                "date": transaction.date.strftime('%Y-%m-%d'),
                "source_short_name": transaction.source.short_name,
                "destination_short_name": transaction.destination.short_name,
                "source": transaction.source.blockchain_address,
                "destination": transaction.destination.blockchain_address,
                "quantity": transaction._destination_quantity,
                "product": transaction.product.name,
                "price": transaction.price,
                "currency": transaction.currency,
                "premium": [
                    (
                        payment.premium.name,
                        payment.amount
                    ) for payment in transaction.premium_paid
                ],
                "card": transaction.card.fairid if transaction.card else "",
                "evidence_type": evidence_type,
                "evidenece_file_hash": evidence_hash
            },
            "ref": None
        }

        data["document"] = {
            k: v for k, v in data["document"].items() if v not in (None, "")
        }

        return data

    def send_trans_data(self, transaction: ExternalTransaction) -> dict:
        """Send data for a specific transaction."""
        data = self.build_submission_data(transaction)

        response = requests.post(
            url=policy_const.PREM_PAID_SEND_TRANS,
            headers=self._get_headers(),
            json=data
        )

        if response.status_code != 200:
            capture_message("Failed to send data to Guardian")
            return {}

        return response.json()
    
    def get_claim_status(self, filter_value) -> int:
        """Fn to check if the data is approved"""
        data = self.get_data(
            policy_const.PREM_PAID_LIST_TRANS,
            policy_const.PREM_PAID_FILTER_TRANS,
            filter_value
        )
        if not data:
            return STATUS_PENDING
        
        status = guard_const.claim_status.get(
            data['option']['status'], STATUS_PENDING
        )
        return status

    def get_document_id(self, filter_value) -> str:
        """Fn to get document id"""
        data = self.get_data(
            policy_const.PREM_PAID_LIST_TRANS,
            policy_const.PREM_PAID_FILTER_TRANS,
            filter_value
        )
        if not data:
            return
        
        document_id = data['document']['id']
        return document_id

    def update_token(self, guardian_claim_id: str, document_id: str):
        """Get token details and update them in db"""
        data = self.get_data(
            policy_const.PREM_PAID_LIST_TOKEN, 
            policy_const.PREM_PAID_FILTER_TOKEN,
            document_id
        )
        if not data:
            return
        
        hash_value = data.get('hash')
        token = self.get_token_details(
            policy_const.PREM_PAID_TRUST_CHAIN, 
            hash_value
        )
        if not token:
            return
        
        token_data = self.get_token_dict(token)
    
        claim = GuardianClaim.objects.get(id=decode(guardian_claim_id))
        for key, value in token_data.items():
            setattr(claim, key, value)
        claim.save()
        claim.trans_claim.status = STATUS_APPROVED
        claim.trans_claim.save()

        return
    
    def set_role(self, role: str):
        """Set role for the user"""
        data = {
            "role": role
        }
        response = requests.post(
            url=policy_const.PREM_PAID_SET_ROLE,
            headers=self._get_headers(),
            data=data
        )
        return
    
    def initiate_policy_workflow(
            self, 
            transaction_id: str,
            claim_id: str,
            guardian_claim_id: str
        ) -> None:
        """Initiate policy workflow"""
        transaction = ExternalTransaction.objects.get(
            id=decode(transaction_id)
        )

        receiver = self.__class__(transaction.destination)
        receiver.set_role(guard_const.CO_OPERATIVE)

        sent = receiver.send_trans_data(transaction)
        if not sent:
            return
        
        guardian_tasks.continue_guardian_claim.apply_async(
            (transaction.idencode, claim_id, guardian_claim_id),
            countdown=600
        )

        return

    def continue_policy_workflow(
            self,
            transaction_id: str,
            claim_id: str,
            guardian_claim_id: str
        ) -> None:
        """verify the transaction and save token details"""
        transaction = ExternalTransaction.objects.get(
            id=decode(transaction_id)
        )

        sender = self.__class__(transaction.source)
        sender.set_role(guard_const.FARMER)

        verified = sender.verify_data(
            policy_const.PREM_PAID_VERIFY_TRANS, 
            policy_const.PREM_PAID_LIST_TRANS,
            policy_const.PREM_PAID_FILTER_TRANS,
            transaction.idencode
        )
        if not verified:
            return

        guardian_tasks.update_token_guardian_claim.apply_async(
            (transaction.idencode, claim_id, guardian_claim_id),
            countdown=600
        )

        return

    def update_token_details(
            self, 
            transaction_id: str, 
            guardian_claim_id: str
        ) -> None:
        """Get toekn details and update it in db"""
        transaction = ExternalTransaction.objects.get(
            id=decode(transaction_id)
        )
        
        sender = self.__class__(transaction.source)
        document_id = sender.get_document_id(transaction.idencode)

        receiver = self.__class__(transaction.destination)    
        receiver.update_token(guardian_claim_id, document_id)

        return
