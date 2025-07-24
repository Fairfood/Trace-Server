import requests
from sentry_sdk import capture_message
from common.library import decode
from v2.claims.constants import STATUS_APPROVED, STATUS_PENDING
from v2.claims.models import GuardianClaim
from v2.supply_chains.models.node import Node
from v2.guardian import policy_const
from v2.guardian import constants as guard_const
from v2.guardian.policies.base import GuardianPolicyBase


class EUDRPreCheckPolicy(GuardianPolicyBase):
    """Concrete class for EUDR Pre-Check policy."""

    def build_submission_data(self, node: Node) -> dict:
        """Build data specific to EUDR policy."""
        data = {
            "document": {
                "name_of_the_cooperative": node.full_name,
                "country": node.country,
                "company_trace_id": node.idencode,
                "address": ", ".join(filter(
                    None, 
                    [
                        node.street, node.city, node.province, node.zipcode
                    ]
                ))
            },
            "ref": None
        }

        data["document"] = {
            k: v for k, v in data["document"].items() if v not in (None, "")
        }

        return data

    def send_data(self, node: Node) -> dict:
        """Send data for a specific node."""
        data = self.build_submission_data(node)

        response = requests.post(
            url=policy_const.EUDR_SEND_DATA,
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
            policy_const.EUDR_LIST_DATA,
            policy_const.EUDR_FILTER_DATA,
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
            policy_const.EUDR_LIST_DATA,
            policy_const.EUDR_FILTER_DATA,
            filter_value
        )
        if not data:
            return
        
        document_id = data['document']['id']
        return document_id
    
    def update_token(self, guardian_claim_id: str, document_id: str):
        """Get token details and update them in db"""
        data = self.get_data(
            policy_const.EUDR_LIST_TOKEN, 
            policy_const.EUDR_FILTER_TOKEN,
            document_id
        )
        if not data:
            return
        
        hash_value = data.get('hash')
        token = self.get_token_details(
            policy_const.EUDR_TRUST_CHAIN, 
            hash_value
        )
        if not token:
            return
        
        token_data = self.get_token_dict(token)

        claim = GuardianClaim.objects.get(id=decode(guardian_claim_id))
        for key, value in token_data.items():
            setattr(claim, key, value)
        claim.save()
        claim.company_claim.status = STATUS_APPROVED
        claim.company_claim.save()

        return
    
    def initiate_policy_workflow(
        self, 
        node_id: str, 
        claim_id:str, 
        guardian_claim_id: str
    ) -> None:
        """Initiate policy workflow"""
        node = Node.objects.get(id=decode(node_id))

        policy = self.__class__()
        policy.send_data(node)

        return