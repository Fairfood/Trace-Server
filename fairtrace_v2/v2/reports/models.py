from common import models as common_models
from common.library import get_file_path_without_random
from django.db import models
from django.utils import timezone
from django_extensions.db.fields import json
from v2.reports.constants import EXCEL
from v2.reports.constants import EXPORT_TYPE_CHOICES
from v2.reports.constants import FILE_TYPE_CHOICES
from v2.reports.constants import PENDING
from v2.reports.constants import STATUS_CHOICES
from v2.reports.managers import ExportQuerySet
from v2.supply_chains.models import Node


class Export(common_models.AbstractBaseModel):
    """Model to store export entries."""

    export_type = models.IntegerField(choices=EXPORT_TYPE_CHOICES)
    file = models.FileField(
        upload_to=get_file_path_without_random, blank=True, null=True
    )
    file_name = models.CharField(max_length=100, null=True, blank=True)
    task_id = models.UUIDField(unique=True, null=True, blank=True)
    filters = json.JSONField(blank=True, null=True)
    rows = models.IntegerField(default=0)
    etc = models.PositiveIntegerField(default=0)
    node = models.ForeignKey(
        Node, on_delete=models.CASCADE, null=True, blank=True
    )
    atc = models.PositiveIntegerField(default=0)
    file_type = models.IntegerField(choices=FILE_TYPE_CHOICES, default=EXCEL)
    status = models.CharField(
        max_length=4, choices=STATUS_CHOICES, default=PENDING
    )

    objects = ExportQuerySet.as_manager()

    def __str__(self):
        """To perform function __str__."""
        return f"{self.file} | {self.pk}"

    @property
    def initial_etc(self):
        """To calculate estimated time of completion from previous entries.

        * Return: etc for a row.
        """
        if not self.etc or self.etc == 0:  # Note Check this
            # noinspection PyUnresolvedReferences
            model = self._meta.model
            atc_rows_map = model.objects.filter(
                export_type=self.export_type
            ).values_list("atc", "rows")
            atc_rows_map = dict(atc_rows_map)
            atc_sum = sum(atc_rows_map.keys())
            rows_sum = sum(atc_rows_map.values())
            try:
                # Adding a 20 % extra in estimate.
                return (atc_sum / rows_sum) * 1.2
            except ZeroDivisionError:
                return 0.05
        return self.etc / self.rows

    @property
    def initial_file_name(self) -> str:
        """Generate file_name for the new file."""
        if not self.file_name:
            export_type_name = dict(EXPORT_TYPE_CHOICES)[self.export_type]
            extension = dict(FILE_TYPE_CHOICES)[self.file_type]
            prefix = export_type_name.capitalize()
            now = timezone.now()
            return prefix + now.strftime("_%Y_%m_%d_%H_%M_%S") + extension
        return str(self.file_name)
