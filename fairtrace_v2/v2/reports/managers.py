from django.db import models
from v2.reports.constants import COMPLETED
from v2.reports.constants import REVOKED


class ExportQuerySet(models.QuerySet):
    """Class to handle ExportQuerySet and functions."""

    def only_completed(self):
        """Returns only completed exports."""
        return self.filter(status=COMPLETED)

    def exclude_revoked(self):
        """Exclude revoked items from qs."""
        return self.exclude(status=REVOKED)
