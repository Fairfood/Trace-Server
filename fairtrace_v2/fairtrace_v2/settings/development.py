"""Settings specific to the development environment.

Setting those are specific to the development environment are specified
here. Common settings params are imported from the base settings file.
"""
import os

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa:F403, F401
from .base import BASE_DIR
from .base import config
from .base import DEPLOYMENT

DEBUG = True

FRONT_ROOT_URL = config.get(
    "app", "FRONT_ROOT_URL", fallback="https://trace-dev.fairfood.nl"
)

ENVIRONMENT = "development"
ALLOWED_HOSTS = ["*"]

CORS_ORIGIN_ALLOW_ALL = True

CORS_ORIGIN_WHITELIST = [
    "http://localhost:8100",
    "http://localhost:4200",
    "http://127.0.0.1",
    "http://trace-dev.fairfood.nl",
]

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), "static")

# Sentry settings

sentry_sdk.init(
    dsn=config.get("libs", "SENTRY_DSN"),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
    ],
    environment=ENVIRONMENT,
    traces_sample_rate=1.0,
    send_default_pii=True,
)
sentry_sdk.set_tag("deployment", DEPLOYMENT)

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

TIME_ZONE = "Asia/Calcutta"

HEDERA_CLAIM_TOPIC_ID = "0.0.415659"
HEDERA_TRANSACTION_TOPIC_ID = "0.0.481029"
