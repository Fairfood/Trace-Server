from django.conf import settings


GUARDIAN_URL = settings.GUARDIAN_URL

#digital receipt policy
DIGITAL_RECEIPT_ID = "685284959bb9c96a574c3db1"
DIG_REC_ROLE_BLOCK_ID = "15fd54a5-a003-491f-9e25-19f804b15290"
DIG_REC_SEND_BLOCK_ID = "58a55985-6f66-4fca-9504-f1783012771b"
DIG_REC_VERIFY_BLOCK_ID = "e30c2884-5417-455a-a83c-3815cfd2e61b"
DIG_REC_LIST_TRANS_BLOCK_ID = "5a765788-666a-4000-872a-fd98bf90a791"
DIG_REC_FILTER_TRANS_BLOCK_ID = "69189192-b14f-4008-bb77-aba998f0a17a"
DIG_REC_LIST_TOKEN_BLOCK_ID = "f5378ebe-4ca4-4c7d-a2f4-4bacd3a450f1"
DIG_REC_TRUST_CHAIN_BLOCK_ID = "14da0f89-1928-4364-bd23-f7c2ff9d32a6"
DIG_REC_FILTER_TOKEN_BLOCK_ID = "e82ed6e1-9910-4771-a336-76e93ef2cf19"

DIG_REC_SET_ROLE = (
    f"{GUARDIAN_URL}/policies/{DIGITAL_RECEIPT_ID}/"
    f"blocks/{DIG_REC_ROLE_BLOCK_ID}"
)
DIG_REC_SEND_TRANS = (
    f"{GUARDIAN_URL}/policies/{DIGITAL_RECEIPT_ID}/"
    f"blocks/{DIG_REC_SEND_BLOCK_ID}"
)
DIG_REC_FILTER_TRANS = (
    f"{GUARDIAN_URL}/policies/{DIGITAL_RECEIPT_ID}/"
    f"blocks/{DIG_REC_FILTER_TRANS_BLOCK_ID}"
)
DIG_REC_LIST_TRANS = (
    f"{GUARDIAN_URL}/policies/{DIGITAL_RECEIPT_ID}/"
    f"blocks/{DIG_REC_LIST_TRANS_BLOCK_ID}"
)
DIG_REC_VERIFY_TRANS = (
    f"{GUARDIAN_URL}/policies/{DIGITAL_RECEIPT_ID}/"
    f"blocks/{DIG_REC_VERIFY_BLOCK_ID}"
)
DIG_REC_FILTER_TOKEN = (
    f"{GUARDIAN_URL}/policies/{DIGITAL_RECEIPT_ID}/"
    f"blocks/{DIG_REC_FILTER_TOKEN_BLOCK_ID}"
)
DIG_REC_LIST_TOKEN = (
    f"{GUARDIAN_URL}/policies/{DIGITAL_RECEIPT_ID}/"
    f"blocks/{DIG_REC_LIST_TOKEN_BLOCK_ID}"
)
DIG_REC_TRUST_CHAIN = (
    f"{GUARDIAN_URL}/policies/{DIGITAL_RECEIPT_ID}/"
    f"blocks/{DIG_REC_TRUST_CHAIN_BLOCK_ID}"
)


#premium paid policy
PREMIUM_PAID_ID = "68527fb29bb9c96a574c3c0c"
PREM_PAID_ROLE_BLOCK_ID = "52eb3253-a417-4913-a0c1-6a2d98bf2054"
PREM_PAID_SEND_BLOCK_ID = "9e9a78ca-dbcd-4de1-8847-55d27c1faf9e"
PREM_PAID_VERIFY_BLOCK_ID = "351d2466-1d18-4c0b-9233-f2ae493aca2a"
PREM_PAID_LIST_TRANS_BLOCK_ID = "b6d3b9aa-ec4a-4b05-8a5a-da79ebe07c4b"
PREM_PAID_FILTER_TRANS_BLOCK_ID = "3d5419d7-1bfe-4de7-9b32-ce8f3086911b"
PREM_PAID_LIST_TOKEN_BLOCK_ID = "1215ba71-bde7-40d0-bd87-c7de90a1391d"
PREM_PAID_TRUST_CHAIN_BLOCK_ID = "76b04ea2-6035-4cfd-b769-77c5c5f6cde3"
PREM_PAID_FILTER_TOKEN_BLOCK_ID = "63466397-5712-4b64-93ac-b486efb8fea2"

PREM_PAID_SET_ROLE = (
    f"{GUARDIAN_URL}/policies/{PREMIUM_PAID_ID}/"
    f"blocks/{PREM_PAID_ROLE_BLOCK_ID}"
)
PREM_PAID_SEND_TRANS = (
    f"{GUARDIAN_URL}/policies/{PREMIUM_PAID_ID}/"
    f"blocks/{PREM_PAID_SEND_BLOCK_ID}"
)
PREM_PAID_FILTER_TRANS = (
    f"{GUARDIAN_URL}/policies/{PREMIUM_PAID_ID}/"
    f"blocks/{PREM_PAID_FILTER_TRANS_BLOCK_ID}"
)
PREM_PAID_LIST_TRANS = (
    f"{GUARDIAN_URL}/policies/{PREMIUM_PAID_ID}/"
    f"blocks/{PREM_PAID_LIST_TRANS_BLOCK_ID}"
)
PREM_PAID_VERIFY_TRANS = (
    f"{GUARDIAN_URL}/policies/{PREMIUM_PAID_ID}/"
    f"blocks/{PREM_PAID_VERIFY_BLOCK_ID}"
)
PREM_PAID_FILTER_TOKEN = (
    f"{GUARDIAN_URL}/policies/{PREMIUM_PAID_ID}/"
    f"blocks/{PREM_PAID_FILTER_TOKEN_BLOCK_ID}"
)
PREM_PAID_LIST_TOKEN = (
    f"{GUARDIAN_URL}/policies/{PREMIUM_PAID_ID}/"
    f"blocks/{PREM_PAID_LIST_TOKEN_BLOCK_ID}"
)
PREM_PAID_TRUST_CHAIN = (
    f"{GUARDIAN_URL}/policies/{PREMIUM_PAID_ID}/"
    f"blocks/{PREM_PAID_TRUST_CHAIN_BLOCK_ID}"
)


#living income policy
LIVING_INCOME_ID = "6851b24c9bb9c96a574c28b3"
LIV_INC_SEND_DATA_BLOCK_ID = "949d8a61-61e7-47eb-aaf3-a01bf1d72b0d"
LIV_INC_FILTER_BLOCK_ID = "f5531b13-026a-483f-b9b6-611405863518"
LIV_INC_LIST_BLOCK_ID = "d5851f8f-2b3e-407d-85eb-6bec60d57a50"
LIV_INC_FILTER_TOKEN_ID = "a9d13e70-1ac4-495c-ad8e-5b8d9a292100"
LIV_INC_LIST_TOKEN_BLOCK_ID = "8fc3f8b2-b340-4cea-a82c-b9ab847eb84c"
LIV_INC_TRUST_CHAIN_BLOCK_ID = "9aa83497-3a9f-41e9-a22b-c8c58fa4a413"

LIV_INC_SEND_DATA = (
    f"{GUARDIAN_URL}/policies/{LIVING_INCOME_ID}/"
    f"blocks/{LIV_INC_SEND_DATA_BLOCK_ID}"
)
LIV_INC_FILTER_DATA = (
    f"{GUARDIAN_URL}/policies/{LIVING_INCOME_ID}/"
    f"blocks/{LIV_INC_FILTER_BLOCK_ID}"
)
LIV_INC_LIST_DATA = (
    f"{GUARDIAN_URL}/policies/{LIVING_INCOME_ID}/"
    f"blocks/{LIV_INC_LIST_BLOCK_ID}"
)
LIV_INC_FILTER_TOKEN = (
    f"{GUARDIAN_URL}/policies/{LIVING_INCOME_ID}/"
    f"blocks/{LIV_INC_FILTER_TOKEN_ID}"
)
LIV_INC_LIST_TOKEN = (
    f"{GUARDIAN_URL}/policies/{LIVING_INCOME_ID}/"
    f"blocks/{LIV_INC_LIST_TOKEN_BLOCK_ID}"
)
LIV_INC_TRUST_CHAIN = (
    f"{GUARDIAN_URL}/policies/{LIVING_INCOME_ID}/"
    f"blocks/{LIV_INC_TRUST_CHAIN_BLOCK_ID}"
)

#eudr pre-check policy
EUDR_PRECHECK_ID = "685271c49bb9c96a574c383c"
EUDR_SEND_DATA_BLOCK_ID = "937a88e7-5d8a-46d0-8f05-32fe755e3393"
EUDR_FILTER_BLOCK_ID = "7cf23d01-f7bf-4e4f-9f16-28595530cc74"
EUDR_LIST_BLOCK_ID = "4ac66def-325c-4002-83df-3176270f1dbe"
EUDR_FILTER_TOKEN_ID = "29cb3f22-2a6b-4266-b166-01a8e5bb6c96"
EUDR_LIST_TOKEN_BLOCK_ID = "89f0fddb-0def-4ad6-8aa6-33e8a6f39487"
EUDR_TRUST_CHAIN_BLOCK_ID = "a11680f8-d846-4bb1-b060-8e835eeb3133"

EUDR_SEND_DATA = (
    f"{GUARDIAN_URL}/policies/{EUDR_PRECHECK_ID}/"
    f"blocks/{EUDR_SEND_DATA_BLOCK_ID}"
)
EUDR_FILTER_DATA = (
    f"{GUARDIAN_URL}/policies/{EUDR_PRECHECK_ID}/"
    f"blocks/{EUDR_FILTER_BLOCK_ID}"
)
EUDR_LIST_DATA = (
    f"{GUARDIAN_URL}/policies/{EUDR_PRECHECK_ID}/"
    f"blocks/{EUDR_LIST_BLOCK_ID}"
)
EUDR_FILTER_TOKEN = (
    f"{GUARDIAN_URL}/policies/{EUDR_PRECHECK_ID}/"
    f"blocks/{EUDR_FILTER_TOKEN_ID}"
)
EUDR_LIST_TOKEN = (
    f"{GUARDIAN_URL}/policies/{EUDR_PRECHECK_ID}/"
    f"blocks/{EUDR_LIST_TOKEN_BLOCK_ID}"
)
EUDR_TRUST_CHAIN = (
    f"{GUARDIAN_URL}/policies/{EUDR_PRECHECK_ID}/"
    f"blocks/{EUDR_TRUST_CHAIN_BLOCK_ID}"
)