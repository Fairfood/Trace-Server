from common.admin import BaseAdmin
from django.contrib import admin
from v2.bulk_uploads.models import DataSheetTemplate, NodeDataSheetTemplates
from v2.bulk_uploads.models import DataSheetTemplateField
from v2.bulk_uploads.models.uploads import DataSheetUpload


class DataSheetTemplateFieldInline(admin.TabularInline):
    """In-line view function for DataSheetTemplateField."""

    model = DataSheetTemplateField
    extra = 0


class DataSheetTemplatedAdmin(BaseAdmin):
    """Customize Node documents admin."""

    inlines = (DataSheetTemplateFieldInline,)


class DataSheetUploadAdmin(BaseAdmin):
    """Customize Node documents admin."""

    list_display = ("template", "node", "file", "idencode")
    autocomplete_fields = ("node",)


class NodeDataSheetTemplatesAdmin(BaseAdmin):
    """Customize Node documents admin."""

    list_display = ("template", "node")
    autocomplete_fields = ("node",)


admin.site.register(DataSheetUpload, DataSheetUploadAdmin)
admin.site.register(DataSheetTemplate, DataSheetTemplatedAdmin)
admin.site.register(NodeDataSheetTemplates, NodeDataSheetTemplatesAdmin)
