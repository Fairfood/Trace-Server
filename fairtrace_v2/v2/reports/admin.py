from common import admin as common_admin
from django.contrib import admin
from v2.reports.models import Export


class ExportAdmin(common_admin.BaseAdmin):
    """Class to handle ExportAdmin and functions."""

    autocomplete_fields = ("node",)


admin.site.register(Export, ExportAdmin)
