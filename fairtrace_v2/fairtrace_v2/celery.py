"""Celery configurations are specified here."""
from __future__ import absolute_import
from __future__ import unicode_literals

import os
from os.path import expanduser

from celery import Celery

# settings.py

home = expanduser("~")

if "DATABASE_URL" not in os.environ:
    app = Celery(
        "celery", broker="redis://", backend="redis://", include=["common"]
    )
else:
    app = Celery(
        "celery",
        broker="redis://127.0.0.1:6379",
        backend="redis://127.0.0.1:6379",
        include=["common"],
    )
BROKER_URL = "redis://127.0.0.1:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.timezone = "UTC"
app.autodiscover_tasks()
