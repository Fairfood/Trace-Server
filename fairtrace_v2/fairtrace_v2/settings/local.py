"""Settings specific to the local environment.

Setting those are specific to the local environment are specified here.
Common settings params are imported from the base settings file.
"""
import os  # noqa

from .base import *  # noqa
from .base import ALLOWED_HOSTS, BASE_DIR, INSTALLED_APPS, config

DEBUG = True

FRONT_ROOT_URL = "http://localhost:8080"

INSTALLED_APPS += [
    "django_nose",
]

ALLOWED_HOSTS += [
    "1b56080e.ngrok.io",
    "127.0.0.1",
    "29f5-87-210-24-91.ngrok.io",
]

ALLOWED_HOSTS += ["*"]

TEST_RUNNER = "django_nose.NoseTestSuiteRunner"

NOSE_ARGS = [
]


CORS_ORIGIN_WHITELIST = [
    "http://localhost",
    "http://127.0.0.1",
]

ENVIRONMENT = "local"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

TIME_ZONE = "Asia/Calcutta"

BC_MIDDLEWARE_BASE_URL = "http://127.0.0.1:7000/v1/registry/requests/"
BLOCKCHAIN_PRIVATE_KEY_PATH = "/etc/secret/fairtrace_v2/hedera"

HEDERA_CLAIM_TOPIC_ID = "0.0.415659"
HEDERA_TRANSACTION_TOPIC_ID = "0.0.481029"

DEBUG_TOOLBAR_PANELS = ("cachalot.panels.CachalotPanel",)
