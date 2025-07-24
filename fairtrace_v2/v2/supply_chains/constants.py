#!/usr/bin/env python
# coding=utf-8
"""Constants of the app supply_chains."""
from __future__ import unicode_literals

# Node type
NODE_TYPE_COMPANY = 1
NODE_TYPE_FARM = 2
NODE_TYPE_VERIFIER = 3
NODE_TYPE_UNKNOWN = 4

NODE_TYPE_CHOICES = (
    (NODE_TYPE_COMPANY, "Company"),
    (NODE_TYPE_FARM, "Farmer"),
    (NODE_TYPE_VERIFIER, "Verifier"),
    (NODE_TYPE_UNKNOWN, "Unknown"),
)

# Node status
NODE_STATUS_ACTIVE = 1
NODE_STATUS_INACTIVE = 2
NODE_STATUS_BLOCK = 3

NODE_STATUS_CHOICES = (
    (NODE_STATUS_ACTIVE, "Active"),
    (NODE_STATUS_INACTIVE, "Inactive"),
    (NODE_STATUS_BLOCK, "Block"),
)

# Node Profile Modes
PROFILE_MODE_NETWORK = 1
PROFILE_MODE_TRANSACTION = 2

NODE_PROFILE_MODE_CHOICES = (
    (PROFILE_MODE_NETWORK, "Network"),
    (PROFILE_MODE_TRANSACTION, "Transaction"),
)

# Company roles
COMPANY_ROLE_ACTOR = 1
COMPANY_ROLE_VERIFIER = 2
COMPANY_ROLE_ACTOR_VERIFIER = 3

COMPANY_ROLE_CHOICES = (
    (COMPANY_ROLE_ACTOR, "Actor"),
    (COMPANY_ROLE_VERIFIER, "Verifier"),
    (COMPANY_ROLE_ACTOR_VERIFIER, "Actor & Verifier"),
)

# Node Disclosure
NODE_DISCLOSURE_CUSTOM = 1
NODE_DISCLOSURE_FULL = 2

NODE_DISCLOSURE_CHOICES = (
    (NODE_DISCLOSURE_CUSTOM, "Custom"),
    (NODE_DISCLOSURE_FULL, "Full"),
)

# Connection statuses
CONNECTION_STATUS_CLAIMED = 101
CONNECTION_STATUS_VERIFIED = 201
CONNECTION_STATUS_REJECTED = 301

CONNECTION_STATUS_CHOICES = (
    (CONNECTION_STATUS_CLAIMED, "Claimed"),
    (CONNECTION_STATUS_VERIFIED, "Verified"),
    (CONNECTION_STATUS_REJECTED, "Rejected"),
)

# Invitation relations
INVITE_RELATION_SUPPLIER = 1
INVITE_RELATION_BUYER = 2

INVITE_RELATION_CHOICES = (
    (INVITE_RELATION_SUPPLIER, "Supplier"),
    (INVITE_RELATION_BUYER, "Buyer"),
)

# Invitation types
INVITATION_TYPE_DIRECT = 1
INVITATION_TYPE_INDIRECT = 2

INVITATION_TYPE_CHOICES = (
    (INVITATION_TYPE_DIRECT, "Direct"),
    (INVITATION_TYPE_INDIRECT, "Indirect"),
)

# Node Document types
DOCUMENT_TYPE_DEFAULT = 1

DOCUMENT_TYPE_CHOICES = ((DOCUMENT_TYPE_DEFAULT, "Default"),)

# Node Member Types
NODE_MEMBER_TYPE_ADMIN = 1
NODE_MEMBER_TYPE_MEMBER = 2
NODE_MEMBER_TYPE_VIEWER = 3

NODE_MEMBER_TYPE_CHOICES = (
    (NODE_MEMBER_TYPE_ADMIN, "Admin"),
    (NODE_MEMBER_TYPE_MEMBER, "Member"),
    (NODE_MEMBER_TYPE_VIEWER, "Viewer"),
)

# Node Actions
NODE_ACTION_COMPLETE_PROFILE = 1
NODE_ACTION_INVITE_ACTORS = 2

NODE_ACTION_CHOICES = (
    (NODE_ACTION_COMPLETE_PROFILE, "Complete Profile"),
    (NODE_ACTION_INVITE_ACTORS, "Invite Actors"),
)

# Selected Theme
SELECTED_THEME_DEFAULT = 1
SELECTED_THEME_CUSTOM = 2
SELECTED_THEME_CHOICES = (
    (SELECTED_THEME_DEFAULT, "Default"),
    (SELECTED_THEME_CUSTOM, "Custom"),
)

# Profile fields for calculating profile completion
FARMER_PROFILE_FIELDS = [
    "first_name",
    "email",
    "phone",
    "description_basic",
    "street",
    "city",
    "province",
    "country",
    "zipcode",
    "image",
    "latitude",
    "longitude",
    "identification_no",
]
COMPANY_PROFILE_FIELDS = [
    "name",
    "description_basic",
    "street",
    "city",
    "province",
    "country",
    "zipcode",
    "latitude",
    "longitude",
    "image",
    "identification_no",
    "phone",
    {"incharge": ["first_name", "email"]},
]

FARMER_ADDITIONAL_FIELDS = (
    ("family_members", "Number of members in family"),
    ("farm_area", "Farm area owned"),
    ("income_from_main_product", "Income from main product"),
    ("income_from_other_sources", "Income from other sources"),
)

COMMON_VISIBLE_FIELDS = {
    "primary_operation": False,
    "identification_no": False,
    "description_basic": False,
    "address": {"street": False, "city": False, "zipcode": False},
}
VISIBLE_FIELDS = {
    NODE_TYPE_COMPANY: {
        **COMMON_VISIBLE_FIELDS,
        **{
            "name": {"name": False},
            "contact_info": {
                "incharge": False,
                "email": False,
                "phone": False,
            },
        },
    },
    NODE_TYPE_FARM: {
        **COMMON_VISIBLE_FIELDS,
        **{
            "name": {"name": False, "first_name": False, "last_name": False},
            "contact_info": {"email": False, "phone": False},
        },
    },
}

# Node plan
NODE_PLAN_BASIC = 1
NODE_PLAN_PREMIUM = 2

NODE_PLAN_CHOICES = (
    (NODE_PLAN_BASIC, "Basic"),
    (NODE_PLAN_PREMIUM, "Premium"),
)

# Node invited by
NODE_INVITED_BY_COMPANY = 1
NODE_INVITED_BY_FFADMIN = 2
NODE_SIGNED_UP = 3

NODE_INVITED_BY_CHOICES = (
    (NODE_INVITED_BY_COMPANY, "Company Invited"),
    (NODE_INVITED_BY_FFADMIN, "FFAdmin Invited"),
    (NODE_SIGNED_UP, "Signed Up"),
)

# Blockchain wallet types
BLOCKCHAIN_WALLET_TYPE_TOPL = 101
BLOCKCHAIN_WALLET_TYPE_HEDERA = 201
BLOCKCHAIN_WALLET_TYPE_GUARDIAN = 301

BLOCKCHAIN_WALLET_TYPES = (
    (BLOCKCHAIN_WALLET_TYPE_TOPL, "TOPL"),
    (BLOCKCHAIN_WALLET_TYPE_HEDERA, "Hedera"),
    (BLOCKCHAIN_WALLET_TYPE_GUARDIAN, "Guardian")
)

BULK_UPLOAD_TYPE_CONNECTION_ONLY = 101
BULK_UPLOAD_TYPE_TRANSACTION_ONLY = 201
BULK_UPLOAD_TYPE_CONNECTION_TRANSACTION = 301

BULK_UPLOAD_TYPE_CHOICES = (
    (BULK_UPLOAD_TYPE_CONNECTION_ONLY, "Connection"),
    (BULK_UPLOAD_TYPE_TRANSACTION_ONLY, "Transaction"),
    (BULK_UPLOAD_TYPE_CONNECTION_TRANSACTION, "Connection & Transaction"),
)

CUSTOM_TEMP_NAME = "Bulk_upload_template"

TRACE_FARMER_REFERENCE_NAME = "Trace farmer card"

APPROXIMATE = "APPROXIMATE"
POLYGON = "POLYGON"
ACCURATE = "ACCURATE"

LOCATION_TYPES = (
    (APPROXIMATE, "APPROXIMATE"),
    (POLYGON, "POLYGON"),
    (ACCURATE, "ACCURATE"),
)

GRANTED = "GRANTED"
REVOKED = "REVOKED"
UNKNOWN = "UNKNOWN"

CONSENT_STATUS_TYPES = (
    (GRANTED, "Consent Granted"),
    (REVOKED, "Consent Revoked"),
    (UNKNOWN, "Consent Unknown"),
)
