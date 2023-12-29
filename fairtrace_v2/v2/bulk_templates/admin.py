from common.admin import BaseAdmin
from django.contrib import admin

from ..supply_chains.admin import UploadFarmerMappingInline
from .models import DynamicBulkUpload
from .models import NodeTemplate
from .models import Template
from .models import TemplateField
from .models import TemplateTypeField


# Register your models here.


class TemplateAdmin(BaseAdmin):
    """Customize Node documents admin."""

    def get_nodes(self, obj):
        """To perform function get_nodes."""
        return "\n".join([p.node_object.name for p in obj.nodes.all()])

    list_display = ("type", "name", "get_nodes", "idencode")


class NodeTemplateAdmin(BaseAdmin):
    """Customize Node documents admin."""

    readonly_fields = BaseAdmin.readonly_fields + ("node",)

    list_display = ("node", "template", "status", "idencode")


class TemplateTypeFieldAdmin(BaseAdmin):
    """Customize Node documents admin."""

    list_display = ("name", "type", "description", "idencode")


class TemplateFieldAdmin(BaseAdmin):
    """Customize Node documents admin."""

    list_display = ("template", "field", "column_pos", "idencode")


class DynamicBulkUploadAdmin(BaseAdmin):
    """Customize Node documents admin."""

    list_display = ("template", "node", "file", "idencode")
    autocomplete_fields = ("node",)
    inlines = [UploadFarmerMappingInline]


admin.site.register(Template, TemplateAdmin)
admin.site.register(NodeTemplate, NodeTemplateAdmin)
admin.site.register(TemplateTypeField, TemplateTypeFieldAdmin)
admin.site.register(TemplateField, TemplateFieldAdmin)
admin.site.register(DynamicBulkUpload, DynamicBulkUploadAdmin)
