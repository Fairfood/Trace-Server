"""Settings specific to the staging environment.

Setting those are specific to the staging environment are specified
here. Common settings params are imported from the base settings file.
"""
import os

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa
from .base import BASE_DIR
from .base import config
from .base import DEPLOYMENT
from .base import INSTALLED_APPS
from .base import MIDDLEWARE

ENVIRONMENT = "staging"

FRONT_ROOT_URL = config.get("app", "FRONT_ROOT_URL")
ALLOWED_HOSTS = [config.get("app", "ALLOWED_ROOT")]

CORS_ORIGIN_WHITELIST = [
    "http://trace.fairfood.nl",
    "https://trace.fairfood.nl",
    "http://trace.fairfood.org",
    "https://trace.fairfood.org",
    "https://" + config.get("app", "ALLOWED_ROOT"),
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

HEDERA_CLAIM_TOPIC_ID = "0.0.3688"
HEDERA_TRANSACTION_TOPIC_ID = "0.0.3689"

HEDERA_NETWORK = 2  # For preview net
