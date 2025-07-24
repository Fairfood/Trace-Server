import requests
import json
from sentry_sdk import capture_message, capture_exception
from typing import Optional
from django.conf import settings
from common.library import hash_file, hash_string
from v2.supply_chains.models.node import Node
from v2.transactions.models import ExternalTransaction
from v2.guardian import constants as guard_const


class GuardianPolicyBase:
    """Base class for Guardian policy interactions."""

    def __init__(self, node: Optional[Node] = None):
        self.node = node
        if node:
            self.access_token = self._get_access_token()
        else:
            self.access_token = self._get_admin_access_token()

    def _login(self) -> dict:
        """Login using guardian credentials."""
        if not self.node.guardian_wallet:
            user_created = self._create_user()
            if not user_created:
                return {}
            
        data = {
            "username": self.node.guardian_wallet.account_id,
            "password": self.node.guardian_wallet.decrypted_private
        }
        
        response = requests.post(
            url=settings.GUARDIAN_USER_LOGIN_URL,
            data=data
        )
        if response.status_code != 200:
            print("Failed to login to Guardian")

        return response.json()

    def _admin_login(self) -> dict:
        """Login using admin guardian credentials."""
        data = {
            "username": settings.GUARDIAN_METH_OWNER_NAME,
            "password": settings.GUARDIAN_SD_USER_PASS
        }
        
        response = requests.post(
            url=settings.GUARDIAN_USER_LOGIN_URL,
            data=data
        )

        if response.status_code != 200:
            print("Failed to login to Guardian")

        return response.json()
    
    def _create_user(self) -> bool:
        """Create user in guardian"""
        try:
            self.node.sync_to_guardian()
        except Exception as e:
            capture_exception(e)
            return False
        return True

    def _get_access_token(self) -> Optional[str]:
        """Get Guardian access token."""
        response = requests.post(
            url=settings.GUARDIAN_USER_ACCESS_TOKEN_URL,
            data=self._login()
        )

        if response.status_code not in [201, 200]:
            capture_message("Failed to get access token from Guardian")
            return None

        return response.json().get("accessToken")
    
    def _get_admin_access_token(self) -> Optional[str]:
        """Get Guardian access token."""
        response = requests.post(
            url=settings.GUARDIAN_USER_ACCESS_TOKEN_URL,
            data=self._admin_login()
        )

        if response.status_code not in [201, 200]:
            capture_message("Failed to get access token from Guardian")
            return None

        return response.json().get("accessToken")

    def _get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def _filter_data(self, filter_block_url: str, value: str) -> bool:
        """Filter data according to value"""
        response = requests.post(
            url=filter_block_url,
            headers=self._get_headers(),
            json={"filterValue": value}
        )

        if response.status_code != 200:
            capture_message("Failed to filter data")
            return False
        
        return True

    def get_data(
            self, 
            list_url: str, 
            filter_url: str, 
            filter_value: str
        ) -> dict:
        """Get the data from policy according to filter"""
        filtered = self._filter_data(filter_url, filter_value)
        if not filtered:
            return
        
        response = requests.get(
            url=list_url,
            headers=self._get_headers()
        )

        if response.status_code != 200:
            capture_message("Failed to get trans data from Guardian")
            return {}
        
        data = response.json().get('data')
        if not data:
            return {}
        return data[0]
        
    def _approve_data(self, data: dict) -> dict:
        """Modify the last transaction data as approved"""
        if not data:
            return {}
        
        data['option']['status'] = "Approved"
        return data

    def verify_data(
            self, 
            verify_url: str, 
            list_url: str,
            filter_url: str, 
            filter_value: str
        ) -> bool:
        """Verify the transaction data in policy"""
        data = self.get_data(list_url, filter_url, filter_value)
        document = self._approve_data(data)
        if not document:
            return

        payload = {
            "document": document,
            "tag": "Button_0"
        }
        response = requests.post(
            url=verify_url,
            headers=self._get_headers(),
            json=payload
        )

        if response.status_code != 200:
            capture_message("Failed to verify data with Guardian")
            return False
        
        return True

    def _get_latest_token(self, token_url: str) -> dict:
        """Get the latest token info."""
        response = requests.get(
            url=token_url,
            headers=self._get_headers()
        )

        if response.status_code != 200:
            capture_message("Failed to get token details from Guardian")
            return {}

        data = response.json().get('data')
        return data[0] if data else {}

    def _filter_token(self, trust_chain_url: str, filter_Value: str) -> None:
        """Filter token base on value"""
        response = requests.post(
            url=trust_chain_url,
            headers=self._get_headers(),
            json={"filterValue": filter_Value}
        )

        if response.status_code != 200:
            capture_message("Failed to filter token data with Guardian")
        
        return

    def get_token_details(
            self, 
            trust_chain_url: str,
            filter_value: str
        ) -> dict:
        """Get and persist filtered token data"""
        self._filter_token(trust_chain_url, filter_value)

        response = requests.get(
            url=trust_chain_url,
            headers=self._get_headers()
        )

        if response.status_code != 200:
            capture_message("Failed to get token details from Guardian")
            return {}

        return response.json()
        
    def get_token_dict(self, token: dict) -> dict:
        """format token data to save in guardian claim"""
        data = token.get('data')
        update_fields = {
            'hash_value': token.get('hash'),
            'extra_info': json.dumps(data),
            'mint_date': data.get('mintDocument', {}).get('date', None),
        }
        return update_fields
    
    def get_evidence_file_hash(self, transaction: ExternalTransaction) -> tuple:
        """Get evidence type and hash based on transaction created"""
        evidence_hash = None
        evidence_type = guard_const.evidence_type['no_evidence']
        data_sheet = transaction.datasheet_uploads.first()
        if data_sheet:
            evidence_type = guard_const.evidence_type['bulk_upload_sheet']
            evidence_hash = data_sheet.file_hash
        elif transaction.card:
            evidence_type = guard_const.evidence_type['card']
            evidence_hash = hash_string(transaction.card.fairid)
        elif transaction.invoice:
            file = requests.get(transaction.invoice, stream=True, timeout=10)
            file.raise_for_status()
            evidence_type = guard_const.evidence_type['photo_of_receipt']
            evidence_hash = hash_file(file)
        return evidence_type, evidence_hash