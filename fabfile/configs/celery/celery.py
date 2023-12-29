"""Celery configurations are specified here."""
from __future__ import absolute_import
from __future__ import unicode_literals

import os
from os.path import expanduser

from celery import Celery
from django.conf import settings
from dotenv import load_dotenv

# settings.py

home = expanduser("~")


env_path = os.path.join(home, ".bash_profile")
load_dotenv(dotenv_path=env_path)

environment = os.getenv("ENVIRONMENT")
print("Environment: ", environment)
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "%s.settings.%s" % (environment, settings.PROJECT_NAME),
)
# app = Celery('cotown')
# for i in os.environ.keys():
#     print i, "|", os.environ[i]
if "DATABASE_URL" not in os.environ:
    print("env local found")
    # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cotown.settings.local")
    app = Celery(
        "celery",
        broker="redis://",
        backend="redis://",
        include=["common.tasks", "blockchain.library"],
    )
else:
    print("non local env")
    app = Celery(
        "celery",
        broker="redis://127.0.0.1:6379",
        backend="redis://127.0.0.1:6379",
        include=["common.tasks", "blockchain.library"],
    )
BROKER_URL = "redis://127.0.0.1:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

app.conf.task_default_queue = "low"
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.timezone = "Africa/Abidjan"
app.autodiscover_tasks()

if __name__ == "__main__":
    app.start()
