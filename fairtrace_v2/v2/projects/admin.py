from common.admin import BaseAdmin
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from .models import NodeCard
from .models import NodeCardHistory
from .models import Payment
from .models import PremiumOption
from .models import Project
from .models import ProjectNode
from .models import ProjectPremium
from .models import ProjectProduct, Synchronization
from . import tasks


# Register your models here.

def start_connect_sync(modeladmin, request, queryset):
    """To perform function create_token."""
    for item in queryset:
        tasks.final_sync.delay(item.owner.pk, item.owner.pk)


class ProjectAdmin(ModelAdmin):
    """Class to handle ProjectAdmin and functions."""

    autocomplete_fields = ("owner",)
    actions = [start_connect_sync]


class PremiumOptionInline(admin.TabularInline):
    """In-line view function for PremiumSlab."""

    model = PremiumOption
    extra = 0


class ProjectPremiumAdmin(ModelAdmin):
    """Class to handle ProjectPremiumAdmin and functions."""

    autocomplete_fields = ("owner",)
    inlines = [PremiumOptionInline]


class PaymentAdmin(BaseAdmin):
    """Class to handle PaymentAdmin and functions."""

    autocomplete_fields = ("source", "destination")
    readonly_fields = ("transaction",)


class NodeCardAdmin(ModelAdmin):
    """Class to handle NodeCardAdmin and functions."""

    readonly_fields = ("creator", "updater", "reference")
    search_fields = ("card_id", "fairid")
    autocomplete_fields = ("node",)
    list_display = ("node", "card_id", "created_on", "updated_on")


class NodeCardHistoryAdmin(BaseAdmin):
    """Class to handle NodeCardHistoryAdmin and functions."""

    autocomplete_fields = ("node",)
    list_display = ("card_id", "node", "status")
    search_fields = ("card_id",)


class ProjectNodeAdmin(ModelAdmin):
    """Class to handle ProjectNodeAdmin and functions."""

    autocomplete_fields = ("node",)
    readonly_fields = ("connection",)
    search_fields = ("node",)

class SynchronizationAdmin(ModelAdmin):
    """Class to handle ProjectNodeAdmin and functions."""

    list_display = ("node", "status", "sync_type")
    raw_id_fields = ("node",)


admin.site.register(Project, ProjectAdmin)
admin.site.register(ProjectNode, ProjectNodeAdmin)
admin.site.register(ProjectProduct, BaseAdmin)
admin.site.register(ProjectPremium, ProjectPremiumAdmin)
admin.site.register(NodeCard, NodeCardAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(NodeCardHistory, NodeCardHistoryAdmin)
admin.site.register(Synchronization, SynchronizationAdmin)
