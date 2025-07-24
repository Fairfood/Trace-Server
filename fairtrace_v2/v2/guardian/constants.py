from v2.claims.constants import STATUS_APPROVED, STATUS_REJECTED
from v2.guardian.policies.digital_receipt import DigitalReceiptPolicy
from v2.guardian.policies.premium_paid import PremiumPaidPolicy
from v2.guardian.policies.eudr_pre_check import EUDRPreCheckPolicy
from v2.guardian.policies.living_income import LivingIncomePolicy


evidence_type = {
    "bulk_upload_sheet": "Bulk Upload Sheet",
    "photo_of_receipt": "Photo of Receipt",
    "card": "Card",
    "no_evidence": "No Evidence"
}

claim_status = {
    "Approved": STATUS_APPROVED,
    "Rejected": STATUS_REJECTED
}

guardian_policies = {
    'digital_receipt': DigitalReceiptPolicy,
    'premium_paid': PremiumPaidPolicy,
    'eudr_pre_check': EUDRPreCheckPolicy,
    'living_income': LivingIncomePolicy
}

APPROVED_OPTION = "Approved"
FARMER = "Farmer"
CO_OPERATIVE = "Co-Operative"
METHODOLOGY_OWNER = "Methodology Owner"
DATA_COLLECTOR = "Data Collector"


MAINNET_URL = "https://mainnet-public.mirrornode.hedera.com"
TESTNET_URL = "https://testnet.mirrornode.hedera.com"
PREVIEWNET_URL = "https://previewnet.mirrornode.hedera.com"

MAINNET = "mainnet"
TESTNET = "testnet"
