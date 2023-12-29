from django.conf import settings

assert settings.ROOT_URL, "ROOT_URL not added in settings"
assert settings.HASHHID_MIN_LENGTH, "HASHHID_MIN_LENGTH not added in settings"
assert settings.HASHHID_SALT, "HASHHID_SALT not added in settings"

assert (
    settings.BLOCKCHAIN_CLIENT_ID
), "BLOCKCHAIN_CLIENT_ID not added in settings"
assert (
    settings.BLOCKCHAIN_PRIVATE_KEY_PATH
), "BLOCKCHAIN_PRIVATE_KEY_PATH not added in settings"
assert (
    settings.BC_MIDDLEWARE_BASE_URL
), "BC_MIDDLEWARE_BASE_URL not added in settings"
# assert settings.BLOCKCHAIN_ENCRYPTION_KEY,
# "BLOCKCHAIN_ENCRYPTION_KEY not added in settings"

assert (
    settings.TREASURY_ACCOUNT_ID
), "TREASURY_ACCOUNT_ID not added in settings"
assert (
    settings.TREASURY_ENCRYPED_PRIVATE
), "TREASURY_ENCRYPED_PRIVATE not added in settings"
