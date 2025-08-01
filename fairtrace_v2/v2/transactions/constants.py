"""Constants for transactions app."""

import enum

# Transaction types
TRANSACTION_TYPE_EXTERNAL = 1
TRANSACTION_TYPE_INTERNAL = 2

TRANSACTION_TYPE_CHOICES = (
    (TRANSACTION_TYPE_EXTERNAL, "External"),
    (TRANSACTION_TYPE_INTERNAL, "Internal"),
)

# Transaction statuses
TRANSACTION_STATUS_CREATED = 1
TRANSACTION_STATUS_DECLINED = 2

TRANSACTION_STATUS_CHOICES = (
    (TRANSACTION_STATUS_CREATED, "Created"),
    (TRANSACTION_STATUS_DECLINED, "Declined"),
)

# External transaction types
EXTERNAL_TRANS_TYPE_OUTGOING = 1
EXTERNAL_TRANS_TYPE_INCOMING = 2
EXTERNAL_TRANS_TYPE_REVERSAL = 3

EXTERNAL_TRANS_TYPE_CHOICES = (
    (EXTERNAL_TRANS_TYPE_OUTGOING, "Outgoing"),
    (EXTERNAL_TRANS_TYPE_INCOMING, "Incoming"),
    (EXTERNAL_TRANS_TYPE_REVERSAL, "Reversal"),
)

# Internal transaction types
INTERNAL_TRANS_TYPE_PROCESSING = 1
INTERNAL_TRANS_TYPE_LOSS = 2
INTERNAL_TRANS_TYPE_MERGE = 3

INTERNAL_TRANS_TYPE_CHOICES = (
    (INTERNAL_TRANS_TYPE_PROCESSING, "Processing"),
    (INTERNAL_TRANS_TYPE_LOSS, "Loss"),
    (INTERNAL_TRANS_TYPE_MERGE, "Merge"),
)

# Transaction modes
TRANSACTION_MODE_MANUAL = 1
TRANSACTION_MODE_SYSTEM = 2

TRANSACTION_MODE_CHOICES = (
    (TRANSACTION_MODE_MANUAL, "Manual"),
    (TRANSACTION_MODE_SYSTEM, "System"),
)

# Client choice types.
CLIENT_WEB = 1
CLIENT_APP = 2

CLIENT_CHOICES = ((CLIENT_WEB, "Web"), (CLIENT_APP, "App"))

# verification method
VERIFICATION_METHOD_MANUAL = 1
VERIFICATION_METHOD_CARD = 2

VERIFICATION_METHOD_CHOICES = (
    (VERIFICATION_METHOD_MANUAL, "Manual"),
    (VERIFICATION_METHOD_CARD, "Card"),
)

# duplicate transaction
DUPLICATE_TXN = "duplicate"

DUPLICATE_TXN_MSG = "Seems like you use the sheet on %s."

DUPLICATE_EX_TXN = 1
DUPLICATE_FARMER = 2

BULK_UPLOAD_TYPE_FARMER = 1
BULK_UPLOAD_TYPE_TXN = 2

FILE_CORRUPTED_MSG = "File is corrupted. Please verify %s"
FILE_CORRUPTED_STATUS = "inComplete"


class CarbonTransactionType(str, enum.Enum):
    """Carbon transaction types"""
    ISSUED = "Issued"
    CRU_TRANSFER = "CRU Transfer"
    RETIRED = "Retired"

CARBON_TRANSACTION_TYPE_MAP = {
    TRANSACTION_TYPE_INTERNAL: {
        INTERNAL_TRANS_TYPE_LOSS: CarbonTransactionType.RETIRED,
    },
    TRANSACTION_TYPE_EXTERNAL: {
        EXTERNAL_TRANS_TYPE_INCOMING: CarbonTransactionType.ISSUED,
        EXTERNAL_TRANS_TYPE_OUTGOING: CarbonTransactionType.CRU_TRANSFER
    }
}