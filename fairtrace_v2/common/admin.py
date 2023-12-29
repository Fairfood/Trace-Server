from django.contrib import admin
from django.contrib.postgres import fields
from django_extensions.db.fields import json
from django_json_widget.widgets import JSONEditorWidget


class BaseAdmin(admin.ModelAdmin):
    """Class to handle BaseAdmin and functions."""

    readonly_fields = (
        "idencode",
        "created_on",
        "updated_on",
        "creator",
        "updater",
    )

    list_display = ("__str__", "idencode")

    formfield_overrides = {
        json.JSONField: {"widget": JSONEditorWidget},
        fields.JSONField: {"widget": JSONEditorWidget},
    }

    def save_model(self, request, obj, form, change):
        """To perform function save_model."""
        # adding the entry for the first time
        if not change:
            obj.creator = request.user
            obj.updater = request.user

        # updating already existing record
        else:
            obj.updater = request.user
        obj.save()


class ReadOnlyAdmin(admin.ModelAdmin):
    """Class to handle ReadOnlyAdmin and functions."""

    def get_readonly_fields(self, request, obj=None):
        """To perform function get_readonly_fields."""
        return list(
            set(
                [field.name for field in self.opts.local_fields]
                + [field.name for field in self.opts.local_many_to_many]
            )
        )

    list_display = ("__str__", "idencode")
