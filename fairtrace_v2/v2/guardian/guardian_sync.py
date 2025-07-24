import requests
from datetime import timedelta
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.core.management.utils import get_random_secret_key
from sentry_sdk import capture_message
from common.library import decode, _encrypt
from v2.blockchain.library import encrypt, decrypt
from v2.supply_chains.models import node as node_models
from v2.supply_chains.constants import BLOCKCHAIN_WALLET_TYPE_GUARDIAN


class GuardianSync:
    """Used to sync node to guardian"""

    def __init__(self, node_id: str):
        self.node = node_models.Node.objects.get(id=decode(node_id))

    def _guardian_login(self, username: str, password: str):
        """fn to login to guardian and return access token"""
        login_data = {"username": username, "password": password}
        response = requests.post(
            settings.GUARDIAN_USER_LOGIN_URL, 
            data=login_data
        )
        if response.status_code != 200:
            capture_message(f"Failed to login to Guardian as {username}")
            raise Exception(f"Failed to login to Guardian as {username}")
        tokens = response.json()

        response = requests.post(
            settings.GUARDIAN_USER_ACCESS_TOKEN_URL,
            data=tokens
        )
        if response.status_code != 201:
            capture_message(f"Failed to get access token for {username}")
            raise Exception(f"Failed to get access token for {username}")

        return response.json()["accessToken"]
    
    def _generate_username(self) -> str:
        """Generate username with readable characters"""
        allowed_chars = "ABCDEFGHJKLMNPQRSTUVWXYZ2345689"
        name = get_random_string(10, allowed_chars=allowed_chars)
        return name

    def _generate_password(self) -> str:
        """generate password"""
        password = get_random_secret_key()[:20]
        return password
    
    def _get_username(self) -> str:
        name = self._generate_username()
        wallet_model = apps.get_model("supply_chains", "BlockchainWallet")
        if wallet_model.objects.filter(account_id=name).exists():
            self._get_username()
        return name

    def _get_password(self) -> str:
        password = self._generate_password()
        wallet_model = apps.get_model("supply_chains", "BlockchainWallet")
        if wallet_model.objects.filter(private=_encrypt(password)).exists():
            self._get_password()
        return password
    
    def _create_guardian_wallet(self):
        """
        Create guardian wallet. credentials used to create account and log 
        in to guardian portal
        """
        username = self._get_username()
        password = self._get_password()
        wallet_model = apps.get_model("supply_chains", "BlockchainWallet")
        wallet = wallet_model.objects.create(
            node=self.node, 
            account_id=username, 
            wallet_type=BLOCKCHAIN_WALLET_TYPE_GUARDIAN,
        )
        wallet.set_private(password)
        return

    def sync_to_guardian(self):
        """Sync the node to the Guardian system."""
        if not self.node.guardian_wallet:
            self._create_guardian_wallet()

        #register user
        guardian_wallet = self.node.guardian_wallet
        register_data = {
            "username": guardian_wallet.account_id,
            "password": guardian_wallet.decrypted_private,
            "password_confirmation": guardian_wallet.decrypted_private,
            "role": "USER"
        }
        response = requests.post(
            settings.GUARDIAN_USER_REGISTER_URL, 
            data=register_data
        )
        if response.status_code != 201:
            print("User already exists or registration failed. Proceeding...")

        #Login and get user access token
        access_token = self._guardian_login(
            guardian_wallet.account_id, guardian_wallet.decrypted_private
        )

        #Get parent DID (Standard Registry)
        response = requests.get(
            settings.GUARDIAN_STANDARD_REGISTRIES_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code != 200:
            capture_message(
                f"Failed to list standard registries {self.node.idencode}"
            )
            raise Exception("Failed to list standard registries")

        parent_did = response.json()[0]["did"]

        #Update user's Hedera info
        hedera_wallet = self.node.hedera_wallet
        if not hedera_wallet:
            capture_message(f"Node-{self.node.idencode} has no hedera wallet")
            raise Exception(f"Node-{self.node.idencode} has no hedera wallet")

        update_data = {
            "parent": parent_did,
            "hederaAccountId": hedera_wallet.account_id,
            "hederaAccountKey": hedera_wallet.decrypted_private,
            "useFireblocksSigning": False,
            "fireblocksConfig": {
                "fireBlocksVaultId": "",
                "fireBlocksAssetId": "",
                "fireBlocksApiKey": "",
                "fireBlocksPrivateiKey": ""
            }
        }
        response = requests.put(
            f"{settings.GUARDIAN_TRANSFER_KEY_URL}{guardian_wallet.account_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=update_data
        )
        if response.status_code != 202:
            capture_message(
                f"Failed to update user {self.node.idencode} in Guardian"
            )
            raise Exception("Failed to update user in Guardian")

        task_id = response.json().get("taskId")
        if task_id:
            requests.get(
                f"{settings.GUARDIAN_URL}/tasks/{task_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        #added a delay beceause of delay while creating user DID in guardian
        from v2.guardian.tasks import assign_user_policies
        eta_time = timezone.now() + timedelta(minutes=10)
        assign_user_policies.apply_async(
            (self.node.idencode,), eta=eta_time
        )
    
    def associate_token(self):
        """Fn to list and associate the user with token"""

        guardian_wallet = self.node.guardian_wallet
        access_token = self._guardian_login(
            guardian_wallet.account_id, guardian_wallet.decrypted_private
        )

        #list tokens
        response = requests.get(
            url=(f"{settings.GUARDIAN_URL}/tokens"),
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code != 200:
            capture_message(f"Failed to list tokens")
            raise Exception(f"Failed to list tokens")

        tokens = response.json()

        for token in tokens:
            draft_token = token.get("draftToken")
            associated = token.get("associated")

            if draft_token or associated:
                continue

            token_id = token.get("tokenId")
            response = requests.put(
                f"{settings.GUARDIAN_URL}/tokens/{token_id}/associate",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                capture_message("Failed to associate token for user")
                raise Exception("Failed to associate token for user")

    def assign_policies(self):
        """Assign policies to user"""
        guardian_wallet = self.node.guardian_wallet

        #Login as admin and assign policies
        root_access_token = self._guardian_login(
            settings.GUARDIAN_SD_USER_NAME, settings.GUARDIAN_SD_USER_PASS
        )

        #fetching policies
        response = requests.get(
            url=(
                f"{settings.GUARDIAN_URL}/permissions/users/"
                f"{guardian_wallet.account_id}/policies"
            ),
            headers={"Authorization": f"Bearer {root_access_token}"}
        )
        if response.status_code != 200:
            capture_message(f"Failed to list policies {self.node.idencode}")
            raise Exception(f"Failed to list policies {self.node.idencode}")

        policies = response.json()
        policy_ids = [p["id"] for p in policies]
        policy_data = {"policyIds": policy_ids, "assign": True}

        #assign policies to node
        response = requests.post(
            url=(
                f"{settings.GUARDIAN_URL}/permissions/users/"
                f"{guardian_wallet.account_id}/policies/assign"
            ),
            headers={"Authorization": f"Bearer {root_access_token}"},
            json=policy_data
        )
        if response.status_code != 201:
            capture_message(f"Failed to assign policies {self.node.idencode}")
            raise Exception(f"Failed to assign policies {self.node.idencode}")
        
        #added a delay beceause of delay to avoid issues
        from v2.guardian.tasks import associate_user_token
        eta_time = timezone.now() + timedelta(minutes=10)
        associate_user_token.apply_async(
            (self.node.idencode,), eta=eta_time
        )
