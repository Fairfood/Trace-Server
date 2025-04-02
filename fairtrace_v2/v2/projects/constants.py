#!/usr/bin/env python
# coding=utf-8
"""Constants of the app projects."""
import enum
from django.conf import settings
from common import constants as com_consts

PREMIUM_TYPE_PER_TRANSACTION = 101
PREMIUM_TYPE_PER_KG = 201
PREMIUM_TYPE_PER_UNIT_CURRENCY = 301
PREMIUM_TYPE_PER_FARMER = 401

PREMIUM_TYPE_CHOICES = (
    (PREMIUM_TYPE_PER_TRANSACTION, "Per transaction"),
    (PREMIUM_TYPE_PER_KG, "Per KG"),
    (PREMIUM_TYPE_PER_UNIT_CURRENCY, "Per unit currency"),
    (PREMIUM_TYPE_PER_FARMER, "Per farmer"),
)

CARD_STATUS_ACTIVE: int = 101
CARD_STATUS_INACTIVE = 201
CARD_STATUS_LOST = 301
CARD_STATUS_BLOCKED = 401

CARD_STATUS_CHOICES = (
    (CARD_STATUS_ACTIVE, "Active"),
    (CARD_STATUS_INACTIVE, "Inactive"),
    (CARD_STATUS_LOST, "Lost"),
    (CARD_STATUS_BLOCKED, "Blocked"),
)

SMS_FARMER_BAL_ENG = (
    "Trace Sales History for {name}\n"
    + "Since {start_date}\nTotal volume: {total_quantity}\nTotal "
    + "Payments: {total_payment} \nPremium Payments: {total_premium}\n"
    + "Average Premium: {avg_premium} / KG\nLast sale\n{last_quantity} on "
    + "{last_sale_date}\nPremium: {last_premium} \nTotal: {last_total}."
)
CARD_ISSUE_STATUS_NEW = 101
CARD_ISSUE_STATUS_REISSUE = 201
CARD_ISSUE_STATUS_REMOVED = 301

CARD_ISSUE_STATUS_CHOICES = (
    (CARD_ISSUE_STATUS_NEW, "Issued"),
    (CARD_ISSUE_STATUS_REISSUE, "Reissued"),
    (CARD_ISSUE_STATUS_REMOVED, "Removed"),
)


SMS_FARMER_BAL_INDO = (
    "Trace Sejarah Penjualan untuk {name}\n"
    + "Sejak {start_date}\nTotal volume: {total_quantity}\nTotal "
    + "Pembayaran: {total_payment} \nTotal Premium: {total_premium}\n"
    + "Rata-rata Premi: {avg_premium} / KG\nPenjualan terakhir\n"
    + " {last_quantity} pada {last_sale_date}\n Premium: {last_premium} \n"
    + " Total: {last_total}."
)

# App transaction types
APP_TRANS_TYPE_OUTGOING = 1
APP_TRANS_TYPE_INCOMING = 2
APP_TRANS_TYPE_LOSS = 3

APP_TRANS_TYPE_CHOICES = (
    (APP_TRANS_TYPE_OUTGOING, "Outgoing"),
    (APP_TRANS_TYPE_INCOMING, "Incoming"),
    (APP_TRANS_TYPE_LOSS, "Loss"),
)

PREMIUM_APPLICABLE_ACTIVITY_BUY = 101
PREMIUM_APPLICABLE_ACTIVITY_SELL = 201

PREMIUM_APPLICABLE_ACTIVITY_CHOICES = (
    (PREMIUM_APPLICABLE_ACTIVITY_BUY, "Activity buy"),
    (PREMIUM_APPLICABLE_ACTIVITY_SELL, "Activity sell"),
)

BAL_SMS_MSG = {
    com_consts.LANGUAGE_ENG: {
        "sender": "+3197010240770",
        "message": SMS_FARMER_BAL_ENG,
        "404_message": "No transactions so far.",
    },
    com_consts.LANGUAGE_INDONESIAN: {
        "sender": "+6285574670328",
        "message": SMS_FARMER_BAL_INDO,
        "404_message": "Tidak ada transaksi sejauh ini.",
    },
}

BASE_TRANSACTION = "TRANSACTION"
BASE_PREMIUM = "PREMIUM"
TRANSACTION_PREMIUM = "TRANSACTION_PREMIUM"

PAYMENT_TYPE_CHOICES = (
    (BASE_TRANSACTION, "TRANSACTION"),
    (BASE_PREMIUM, "PREMIUM"),
    (TRANSACTION_PREMIUM, "TRANSACTION_PREMIUM"),
)

INCOMING = "INCOMING"
OUTGOING = "OUTGOING"

PAYMENT_DIRECTION_CHOICES = (
    (INCOMING, "INCOMING"),
    (OUTGOING, "OUTGOING"),
)

PREMIUM_CATEGORY_CHOICES = (
    (BASE_PREMIUM, "PREMIUM"),
    (TRANSACTION_PREMIUM, "TRANSACTION_PREMIUM"),
)

CARD_VERIFICATION = "CARD"
INVOICE_VERIFICATION = "INVOICE"
NO_VERIFICATION = "NOT_VERIFIED"

VERIFICATION_METHOD_CHOICES = (
    (CARD_VERIFICATION, "CARD_VERIFICATION"),
    (INVOICE_VERIFICATION, "INVOICE_VERIFICATION"),
    (NO_VERIFICATION, "NO_VERIFICATION"),
)

NORMAL = "NORMAL"
MANUAL = "MANUAL"
OPTIONS = "OPTIONS"

CALCULATION_TYPE_CHOICES = (
    (NORMAL, "NORMAL"),  # Apply normal calculation with cost.
    (MANUAL, "MANUAL"),  # Apply manual cost to calculate.
    (OPTIONS, "OPTIONS"),  # Cost taken from OPTIONS.
)

SYNC_STATUS_IN_PROGRESS = "IN_PROGRESS"
SYNC_STATUS_SUCCESS = "SUCCESS"
SYNC_STATUS_FAILED = "FAILED"

SYNC_STATUS_CHOICES = (
    (SYNC_STATUS_IN_PROGRESS, "IN_PROGRESS"),
    (SYNC_STATUS_SUCCESS, "SUCCESS"),
    (SYNC_STATUS_FAILED, "FAILED"),
)

SYNC_TYPE_CONNCET = "CONNECT"
SYNC_TYPE_NAVIGATE = "NAVIGATE"

SYNC_TYPE_CHOICES = (
    (SYNC_TYPE_CONNCET, "CONNECT"),
    (SYNC_TYPE_NAVIGATE, "NAVIGATE"),
)


class ConnectURL(enum.Enum):
    """Trace Connect API endpoints"""
    BASE_URL = f"{settings.ROOT_URL}/connect/v1/"
    LOGIN = BASE_URL + "auth/login/"
    FARMERS = BASE_URL + "supply-chains/farmers/"
    ENTITY_CARDS = BASE_URL + "supply-chains/entity-cards/"
    PRODUCT_TRANSACTIONS = BASE_URL + "transactions/product-transactions/"