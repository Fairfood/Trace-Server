"""Constants used in the app Accounts."""
# Validity in Minutes
_30_MINUTES = 30  # 30 Minutes
_1_DAY = 1440  # 24 hours
_2_DAY = 2880  # 48 hours
_365_DAYS = 525600  # 365 days

# User language

LANGUAGE_ENG = 1
LANGUAGE_DUTCH = 2
# Choices
LANGUAGE_CHOICES = ((LANGUAGE_ENG, "English"), (LANGUAGE_DUTCH, "Dutch"))

# Invitation Types
USER_TYPE_NODE_USER = 1
USER_TYPE_FAIRFOOD_ADMIN = 2
USER_TYPE_FAIRFOOD_MANAGER = 3

# Choices
USER_TYPE_CHOICES = (
    (USER_TYPE_NODE_USER, "Node user"),
    (USER_TYPE_FAIRFOOD_ADMIN, "Fairfood admin"),
    (USER_TYPE_FAIRFOOD_MANAGER, "Fairfood manager"),
)

# Validation token type
VTOKEN_TYPE_VERIFY_EMAIL = 1
VTOKEN_TYPE_CHANGE_EMAIL = 2
VTOKEN_TYPE_RESET_PASS = 3
VTOKEN_TYPE_OTP = 4
VTOKEN_TYPE_MAGIC_LOGIN = 5
VTOKEN_TYPE_INVITE = 6
VTOKEN_TYPE_NOTIFICATION = 7

# Choices
VTOKEN_TYPE_CHOICES = (
    (VTOKEN_TYPE_VERIFY_EMAIL, "Verify Email"),
    (VTOKEN_TYPE_CHANGE_EMAIL, "Change Email"),
    (VTOKEN_TYPE_RESET_PASS, "Reset Password"),
    (VTOKEN_TYPE_OTP, "OTP"),
    (VTOKEN_TYPE_MAGIC_LOGIN, "Magic Link"),
    (VTOKEN_TYPE_INVITE, "Invite"),
    (VTOKEN_TYPE_NOTIFICATION, "Notification"),
)

# Validity
TOKEN_VALIDITY = {
    VTOKEN_TYPE_VERIFY_EMAIL: _365_DAYS,
    VTOKEN_TYPE_CHANGE_EMAIL: _365_DAYS,
    VTOKEN_TYPE_RESET_PASS: _2_DAY,
    VTOKEN_TYPE_OTP: _1_DAY,
    VTOKEN_TYPE_MAGIC_LOGIN: _2_DAY,
    VTOKEN_TYPE_INVITE: _365_DAYS,
    VTOKEN_TYPE_NOTIFICATION: _365_DAYS,
}

# Validation token status

VTOKEN_STATUS_UNUSED = 1
VTOKEN_STATUS_USED = 2
# Choices
VTOKEN_STATUS_CHOICES = (
    (VTOKEN_STATUS_UNUSED, "Not used"),
    (VTOKEN_STATUS_USED, "Used"),
)

# Device types

DEVICE_TYPE_ANDROID = 1
DEVICE_TYPE_IOS = 2
DEVICE_TYPE_WEB = 3
# Choices
DEVICE_TYPE_CHOICESS = (
    (DEVICE_TYPE_ANDROID, "Android"),
    (DEVICE_TYPE_IOS, "iOS"),
    (DEVICE_TYPE_WEB, "web"),
)

MOBILE_DEVICE_TYPES = [DEVICE_TYPE_ANDROID, DEVICE_TYPE_IOS]

USER_STATUS_CREATED = 1
USER_STATUS_COMPANY_ADDED = 2

USER_STATUS_CHOICES = (
    (USER_STATUS_CREATED, "Created"),
    (USER_STATUS_COMPANY_ADDED, "Company Added"),
)

# Messages

MESSAGE_USER_OTP = (
    "%s is your OTP for Fairfood and it will expire in %s " "minutes."
)
MESSAGE_OTP_INVALID = "Invalid OTP."
MESSAGE_OTP_EXPIRED = "OTP is expired/used. Please re-initiate."
MESSAGE_OTP_VALIDATED = "OTP Validated Successfully"

GOOGLE_ID_TOKEN_INFO_URL = "https://www.googleapis.com/oauth2/v3/tokeninfo"
GOOGLE_ACCESS_TOKEN_OBTAIN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
