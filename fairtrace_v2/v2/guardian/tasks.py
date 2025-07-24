from celery import shared_task
from sentry_sdk import capture_message
from common.library import decode
from v2.claims.models import Claim, GuardianClaim
from v2.claims.constants import STATUS_PENDING
from v2.guardian.constants import guardian_policies
from .claim_status import check_claim_status
from v2.guardian.guardian_sync import GuardianSync


@shared_task(name="sync_all_nodes_to_guardian")
def sync_all_nodes_to_guardian():
    """
    Sync all nodes to the guardian.
    """
    # Get all nodes
    from v2.supply_chains.models.node import Node
    nodes = Node.objects.all()

    for node in nodes:
        print(f"Syncing node {node.email} to guardian")
        node.sync_to_guardian()
        print(f"Node {node.email} synced to guardian")


@shared_task(name="initiate_guardian_claim", queue="low")
def initiate_guardian_claim(
        obj_id: str, 
        claim_id: str, 
        guardian_claim_id: str
    ) -> bool:
    """Initiate guardian claim workflow"""

    claim = Claim.objects.get(id=decode(claim_id))
    
    policy = guardian_policies.get(claim.key)
    if not policy:
        capture_message(f"Policy with name {claim.name} Not Found")
        return

    policy().initiate_policy_workflow(obj_id, claim_id, guardian_claim_id)
    return True


@shared_task(name="continue_guardian_claim", queue="low")
def continue_guardian_claim(
        obj_id: str, 
        claim_id: str, 
        guardian_claim_id: str
    ) -> bool:
    """continue guardian claim workflow"""

    claim = Claim.objects.get(id=decode(claim_id))
    
    policy = guardian_policies.get(claim.key)
    if not policy:
        capture_message(f"Policy with name {claim.name} Not Found")
        return

    policy().continue_policy_workflow(obj_id, claim_id, guardian_claim_id)
    return True


@shared_task(name="update_token_guardian_claim", queue="low")
def update_token_guardian_claim(
        obj_id: str, 
        claim_id: str, 
        guardian_claim_id: str
    ) -> bool:
    """task to get and update token from guardian into db"""

    claim = Claim.objects.get(id=decode(claim_id))
    
    policy = guardian_policies.get(claim.key)
    if not policy:
        capture_message(f"Policy with name {claim.name} Not Found")
        return

    policy().update_token_details(obj_id, guardian_claim_id)
    return True


@shared_task(name="check_guardian_claim_status")
def check_guardian_claim_status():
    """task to check celey status"""
    check_claim_status()
    return True


@shared_task(name="assign_user_policies", queue="low")
def assign_user_policies(node_id: str) -> bool:
    """task to assign user policies"""
    GuardianSync(node_id).assign_policies()
    return True


@shared_task(name="associate_user_token", queue="low")
def associate_user_token(node_id: str) -> bool:
    """task to assign user policies"""
    GuardianSync(node_id).associate_token()
    return True


@shared_task(name="validate_and_initiate_guardian_claim")
def validate_and_initiate_guardian_claim() -> bool:
    """
    Re-evaluates guardian transaction claims that were previously skipped 
    due to invalid wallets, and initiates the guardian claim process for 
    those whose wallets are now valid.

    This task checks all pending guardian transaction claims and verifies 
    whether both the source and destination nodes involved in the transaction 
    now have valid Hedera wallets. If both wallets are valid, it triggers the 
    guardian claim initiation.

    Returns:
        bool: Always returns True after processing all eligible claims.
    """

    guardian_claims = GuardianClaim.objects.filter(
        trans_claim__status=STATUS_PENDING
    )
    for guardian_claim in guardian_claims:
        transaction = guardian_claim.trans_claim.transaction
        
        if not (
            transaction.source.has_valid_hedera_wallet() and
            transaction.destination.has_valid_hedera_wallet()
        ):
            continue
        
        initiate_guardian_claim.delay(
            transaction.idencode, 
            guardian_claim.trans_claim.claim.idencode, 
            guardian_claim.idencode
        )
    return True