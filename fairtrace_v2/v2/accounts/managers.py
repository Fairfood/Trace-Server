from django.db import models
from django.db.models import OuterRef, Max, Subquery


class UserClientVersionQuerySet(models.QuerySet):

    def only_latest_versions(self):
        return self
