from sentry_sdk import capture_message
from django.db.models import Q
from django.db.models.query import QuerySet
from common.library import decode
from v2.claims.constants import STATUS_APPROVED, STATUS_PENDING
from v2.claims.models import GuardianClaim
from v2.guardian.constants import guardian_policies


def get_guardian_claims(claim_id: str = None) -> QuerySet:
    """Get guardian claims"""
    guardian_claims = GuardianClaim.objects.filter(
        Q(trans_claim__status=STATUS_PENDING) |
        Q(company_claim__status=STATUS_PENDING)
    )
    if claim_id:
        guardian_claims = guardian_claims.filter(id=decode(claim_id))
    return guardian_claims


def check_claim_status(
        filter_value: str = None, 
        guardian_claim_id: str = None
    ) -> int:
    """fn to check status and update status of claims"""
    guardian_claims = get_guardian_claims(guardian_claim_id)
    last_status = STATUS_PENDING

    for guardian_claim in guardian_claims:
        if guardian_claim.company_claim:
            filter_id = guardian_claim.company_claim.node.idencode
            attached_claim = guardian_claim.company_claim
        else:
            filter_id = guardian_claim.trans_claim.transaction.idencode
            attached_claim = guardian_claim.trans_claim
        
        policy_class = guardian_policies.get(attached_claim.claim.key)
        if not policy_class:
            capture_message(
                f"Policy with key {attached_claim.claim.key} Not Found"
            )
        
        filter_value = filter_value or filter_id

        if guardian_claim.trans_claim:
            receiver = policy_class(attached_claim.transaction.destination)
            sender = policy_class(attached_claim.transaction.source)
        
            claim_status = sender.get_claim_status(filter_value)
            attached_claim.status = claim_status
            attached_claim.save()
            
            if claim_status == STATUS_APPROVED:    
                document_id = sender.get_document_id(filter_value)
                receiver.update_token(guardian_claim.idencode, document_id)
                
        else:
            policy = policy_class()
            claim_status = policy.get_claim_status(filter_value)
            attached_claim.status = claim_status
            attached_claim.save()

            if claim_status == STATUS_APPROVED:
                document_id = policy.get_document_id(filter_value)
                policy.update_token(guardian_claim.idencode, document_id)
        
        last_status = attached_claim.status
        
    return last_status