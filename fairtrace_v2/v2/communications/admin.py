"""Django admin manager of the app communications."""
from django.contrib import admin
from v2.accounts.constants import USER_TYPE_NODE_USER
from v2.accounts.models import FairfoodUser

from .models import Notification


class NotificationAdmin(admin.ModelAdmin):
    """Class view to customize Notification admin."""

    list_display = (
        "user",
        "title_en",
        "type",
        "event",
        "action",
        "is_read",
    )
    list_filter = (
        "type",
        "event",
        "action",
    )
    readonly_fields = (
        "user",
        "creator",
        "updater",
        "actor_node",
        "target_node",
    )

    def get_queryset(self, request):
        """Query set to list objects."""
        queryset = super().get_queryset(request)
        try:
            user = FairfoodUser.objects.get(user=request.user)
            if user.type != USER_TYPE_NODE_USER:
                queryset = queryset.filter(user=user)
        except Exception:
            pass
        return queryset


admin.site.register(Notification, NotificationAdmin)
