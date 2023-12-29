"""Settings specific to the production environment.

Setting those are specific to the production environment are specified
here. Common settings params are imported from the base settings file.
"""
import os

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa:F403,F401
from .base import BASE_DIR
from .base import CELERY_BEAT_SCHEDULE
from .base import config
from .base import crontab
from .base import DEPLOYMENT
from .base import INSTALLED_APPS
from .base import MIDDLEWARE


ENVIRONMENT = "production"

FRONT_ROOT_URL = "https://trace.fairfood.org"
ALLOWED_HOSTS = [
    "v2.api.fairfood.org",
]

CORS_ORIGIN_WHITELIST = [
    "http://trace.fairfood.nl",
    "https://trace.fairfood.nl",
    "http://trace.fairfood.org",
    "https://trace.fairfood.org",
]

INSTALLED_APPS += [
    "django_otp",
    "django_otp.plugins.otp_totp",
]

MIDDLEWARE += [
    # MFA OTP
    "django_otp.middleware.OTPMiddleware"
]

# Sentry settings

sentry_sdk.init(
    dsn=config.get("libs", "SENTRY_DSN"),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
    ],
    traces_sample_rate=1.0,
    environment=ENVIRONMENT,
)
sentry_sdk.set_tag("deployment", DEPLOYMENT)

# REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
#     'rest_framework.throttling.AnonRateThrottle',
#     'rest_framework.throttling.UserRateThrottle'
# ]
# REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
#     'anon': '5/min',
#     'user': '50000/day'
# }

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), "static")

# Media file settings for S3

AWS_ACCESS_KEY_ID = config.get("libs", "AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config.get("libs", "AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config.get("libs", "AWS_STORAGE_BUCKET_NAME")
AWS_QUERYSTRING_AUTH = False
AWS_PRELOAD_METADATA = True
# AWS_DEFAULT_ACL = 'public'
DEFAULT_FILE_STORAGE = "s3_folder_storage.s3.DefaultStorage"
DEFAULT_S3_PATH = "media"
MEDIA_ROOT = "/%s/" % DEFAULT_S3_PATH
MEDIA_URL = "//%s.s3.amazonaws.com/media/" % AWS_STORAGE_BUCKET_NAME

TIME_ZONE = "UTC"

HEDERA_ACCOUNT_EXPLORER = config.get(
    "libs",
    "HEDERA_ACCOUNT_EXPLORER",
    fallback="https://app.dragonglass.me/hedera/accounts/{account_id}",
)
HEDERA_TRANSACTION_EXPLORER = config.get(
    "libs",
    "HEDERA_TRANSACTION_EXPLORER",
    fallback="https://v2.explorer.kabuto.sh/transaction/{address}",
)

HEDERA_CLAIM_TOPIC_ID = "0.0.284293"
HEDERA_TRANSACTION_TOPIC_ID = "0.0.284295"

HEDERA_NETWORK = 3  # For main net

CELERY_BEAT_SCHEDULE["export-app-txn"] = {
    "task": "export_app_txn",
    "schedule": crontab(hour=6, minute=0),
}
