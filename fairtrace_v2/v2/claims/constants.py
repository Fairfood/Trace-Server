"""Constants used in claims app."""
from v2.claims import verifiers
from django.utils.translation import gettext_lazy as _

# Claim scope
CLAIM_SCOPE_GLOBAL = 1
CLAIM_SCOPE_LOCAL = 2

CLAIM_SCOPE_CHOICES = (
    (CLAIM_SCOPE_GLOBAL, "Global"),
    (CLAIM_SCOPE_LOCAL, "Local"),
)

# Claim types
CLAIM_TYPE_PRODUCT = 1
CLAIM_TYPE_COMPANY = 2

CLAIM_TYPE_CHOICES = (
    (CLAIM_TYPE_PRODUCT, "Product"),
    (CLAIM_TYPE_COMPANY, "Company"),
)

# Verification types
VERIFICATION_TYPE_SYSTEM = 1
VERIFICATION_TYPE_MANUAL = 2

VERIFICATION_TYPE_CHOICES = (
    (VERIFICATION_TYPE_SYSTEM, "System"),
    (VERIFICATION_TYPE_MANUAL, "Manual"),
)

# Inheritance types
INHERITANCE_TYPE_ALL = 1  # Claim is inherited every time
INHERITANCE_TYPE_NONE = 2  # Claim is never inherited
INHERITANCE_TYPE_PRODUCT = (
    3  # Claim is inherited if destination product # remains the same
)

INHERITANCE_TYPE_CHOICES = (
    (INHERITANCE_TYPE_ALL, "All"),
    (INHERITANCE_TYPE_NONE, "None"),
    (INHERITANCE_TYPE_PRODUCT, "Product"),
)

# Verified by
VERIFIED_BY_SECOND_PARTY = 1
VERIFIED_BY_THIRD_PARTY = 2
VERIFIED_BY_SYSTEM = 3
VERIFIED_BY_NONE = 4

VERIFIED_BY_CHOICES = (
    (VERIFIED_BY_SECOND_PARTY, "Second"),
    (VERIFIED_BY_THIRD_PARTY, "Third"),
    (VERIFIED_BY_SYSTEM, "System"),
    (VERIFIED_BY_NONE, "None"),
)

# Claim attached from
ATTACHED_DIRECTLY = 1
ATTACHED_FROM_TRANSACTION = 2
ATTACHED_BY_INHERITANCE = 3

ATTACHED_FROM_CHOICES = (
    (ATTACHED_DIRECTLY, "Directly"),
    (ATTACHED_FROM_TRANSACTION, "From Transaction"),
    (ATTACHED_BY_INHERITANCE, "Inherited"),
)

# Claim statuses
STATUS_PENDING = 1
STATUS_APPROVED = 2
STATUS_REJECTED = 3
STATUS_PARTIAL = 4

STATUS_CHOICES = (
    (STATUS_PENDING, "Pending"),
    (STATUS_APPROVED, "Approved"),
    (STATUS_REJECTED, "Rejected"),
    (STATUS_PARTIAL, "Partial"),
)

# Field types
FIELD_TYPE_TEXT = 1
FIELD_TYPE_OPTION = 2
FIELD_TYPE_FILE = 3

FIELD_TYPE_CHOICES = (
    (FIELD_TYPE_TEXT, "Text"),
    (FIELD_TYPE_OPTION, "Option"),
    (FIELD_TYPE_FILE, "File"),
)

# System verifiers
TRACEABLE_GUJI_REGION_VERIFIER = "guji_traceable"
GOOD_PRICE_VERIFIER = "good_price"
FARMER_VERIFIER = "farmer"

VERIFIER_CHOICES = (
    (TRACEABLE_GUJI_REGION_VERIFIER, "Traceable Guji Region Verifier"),
    (GOOD_PRICE_VERIFIER, "Good Price Verifier"),
    (FARMER_VERIFIER, "Farmer verifier"),
)

# Criterion ferification functions
CRITERION_VERIFIERS = {
    TRACEABLE_GUJI_REGION_VERIFIER: verifiers.TraceableGujiClaim,
    GOOD_PRICE_VERIFIER: verifiers.GoodPriceClaim,
    FARMER_VERIFIER: verifiers.FarmerClaim,
}

# Verification method
VERIFICATION_METHOD_OTHER = 1
VERIFICATION_METHOD_MAP = 2

VERIFICATION_METHOD_CHOICES = (
    (VERIFICATION_METHOD_OTHER, "Other"),
    (VERIFICATION_METHOD_MAP, "Map"),
)

TRACE = "trace"
GUARDIAN = "guardian"

CLAIM_PROCESSOR_CHOICES = (
    (TRACE, _('Trace')),
    (GUARDIAN, _('Guardian')),
)