from common.admin import BaseAdmin
from django.contrib import admin

from .models import Activity


# Register your models here.


class ActivityAdmin(BaseAdmin):
    """Class to handle ActivityAdmin and functions."""

    def get_text(self, obj):
        """To perform function get_text."""
        return "%s      %s" % (obj.user_text, obj.node_text)

    list_display = ("idencode", "user", "node", "activity_type", "get_text")

    readonly_fields = (
        "user",
        "node",
        "supply_chain",
        "user_text",
        "node_text",
        "activity_type",
        "object_id",
        "object_type",
        "creator",
        "updater",
        "updated_on",
        "created_on",
    )


admin.site.register(Activity, ActivityAdmin)
