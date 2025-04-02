from common.admin import BaseAdmin
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from . import cache_handlers
from ..products.models import Batch
from .models import CITheme, ConsumerInterfaceClaimIntervention
from .models import ConsumerInterfaceActor
from .models import ConsumerInterfaceClaim
from .models import ConsumerInterfaceProduct
from .models import ConsumerInterfaceStage
from .models import DashboardTheme
from .models import MenuItem
from .models import NodeStats
from .models import Program
from .models import ProgramStat


# Register your models here.


def copy_theme(modeladmin, request, queryset):
    """To perform function copy_theme."""
    for item in queryset:
        item.create_copy()


def clear_filesystem_cache(modeladmin, request, queryset):
    """To perform function clear_filesystem_cache."""
    if queryset.count() > 5:
        raise Exception("Select less than 5 items")
    for item in queryset:
        batch_ids = cache_handlers.get_batches(item.id)
        batches = Batch.objects.filter(pk__in=batch_ids)
        for batch in batches:
            cache_handlers.clear_ci_map_cache.delay(batch.id)
            cache_handlers.clear_ci_stage_cache.delay(batch.id)
            cache_handlers.clear_ci_claim_cache.delay(batch.id)


copy_theme.short_description = "Copy theme"


class ConsumerInterfaceStageAdmin(BaseAdmin):
    """Class to handle ConsumerInterfaceStageAdmin and functions."""

    list_display = ("theme", "position", "operation")


class ThemeAdmin(TranslationAdmin):
    """Class to handle ThemeAdmin and functions."""
    list_display = ("node", "name", "batch")
    search_fields = ("node", "name",)
    list_select_related = (
        "node__farmer",
        "node__company",
        "batch",
        "batch__product",
    )
    actions = [copy_theme, clear_filesystem_cache]
    readonly_fields = ("batch",)
    autocomplete_fields = ("node",)

    fieldsets = (
        ("Trace", {"fields": ("node", "name", "batch", "is_public")}),
        ("Claim data", {"fields": ("default_claim",)}),
        ("Program data", {"fields": ("program",)}),
        (
            "Colours",
            {
                "fields": (
                    "primary_colour",
                    "primary_colour_light",
                    "secondary_colour",
                    "text_colour",
                    "action_colour",
                    "primary_colour_shade_1",
                    "primary_colour_shade_2",
                    "primary_colour_shade_3",
                    "primary_colour_shade_4",
                    "primary_colour_shade_5",
                    "stroke_colour",
                    "page_bg_colour",
                )
            },
        ),
        (
            "Brand",
            {
                "fields": (
                    "brand_name",
                    "brand_logo",
                    "brand_website",
                    "show_brand_footer",
                ),
            },
        ),
        (
            "Page Banner",
            {
                "fields": (
                    "banner_text",
                    "banner_text_colour",
                    "banner_image",
                    "mobile_banner_image",
                    "banner_farmer_icon",
                    "banner_mode",
                )
            },
        ),
        (
            "Video Banner",
            {
                "fields": ("video_title", "video_description", "video_url"),
            },
        ),
        (
            "Action button",
            {
                "fields": (
                    "action_button_text",
                    "action_button_url",
                    "show_action_button",
                    "show_share_button",
                ),
            },
        ),
        (
            "Social media",
            {
                "fields": (
                    "facebook_url",
                    "linkedin_url",
                    "instagram_url",
                    "twitter_url",
                ),
            },
        ),
        (
            "Social sharing options",
            {
                "fields": (
                    "share_facebook_title",
                    "share_facebook_body",
                    "share_linkedin_title",
                    "share_linkedin_body",
                    "share_twitter_title",
                    "share_twitter_body",
                    "share_whatsapp_title",
                    "share_whatsapp_body",
                ),
            },
        ),
        (
            "Placeholder images",
            {
                "fields": (
                    "product_placeholder",
                    "farmer_placeholder",
                    "actor_placeholder",
                )
            },
        ),
        ("Languages", {"fields": ("available_languages", "default_language")}),
        ("Theme data", {"fields": ("farmer_description",)}),
        ("Version data", {"fields": ("version",)}),
    )


class ProgramStatsInline(admin.TabularInline):
    """In-line view function for Sub-element model."""

    extra = 0
    model = ProgramStat
    fields = ("name", "name_nl", "value", "symbol", "is_visible")


class ConsumerInterfaceClaimInterventionInline(admin.TabularInline):
    """In-line view function for ConsumerInterfaceClaimIntervention."""

    model = ConsumerInterfaceClaimIntervention
    extra = 0
    fields = ("name", "description", "name_nl", "description_nl", "image",
              "external_link")


class ConsumerInterfaceClaimInterventionAdmin(BaseAdmin):
    """In-line view function for ConsumerInterfaceClaimIntervention."""

    list_display = ("name", )


class DashboardThemeAdmin(BaseAdmin):
    """Class to handle DashboardThemeAdmin and functions."""

    list_select_related = (
        "node__farmer",
        "node__company",
    )
    search_fields = [
        "node__company__name",
        "node__farmer__first_name",
        "node__farmer__last_name",
    ]
    autocomplete_fields = ("node",)
    fieldsets = (
        ("Node", {"fields": ("node", "image", "default")}),
        (
            "Colours",
            {
                "fields": (
                    "colour_primary_alpha",
                    "colour_primary_beta",
                    "colour_primary_gamma",
                    "colour_primary_delta",
                    "colour_secondary",
                    "colour_font_alpha",
                    "colour_font_beta",
                    "colour_font_negative",
                    "colour_border_alpha",
                    "colour_border_beta",
                    "colour_background",
                    "colour_sidebar",
                    "colour_map_background",
                    "colour_map_clustor",
                    "colour_map_marker",
                    "colour_map_selected",
                    "colour_map_marker_text",
                )
            },
        ),
    )


class ConsumerInterfaceProductAdmin(BaseAdmin):
    """Class to handle ConsumerInterfaceProductAdmin and functions."""

    list_display = ("theme", "product", "name")


class ConsumerInterfaceActorAdmin(BaseAdmin):
    """Class to handle ConsumerInterfaceActorAdmin and functions."""

    list_display = ("theme", "actor", "name")
    autocomplete_fields = ("actor",)


class ConsumerInterfaceClaimAdmin(BaseAdmin):
    """Class to handle ConsumerInterfaceClaimAdmin and functions."""

    list_display = ("theme", "claim")
    inlines = [ConsumerInterfaceClaimInterventionInline]


class NodeStatsAdmin(BaseAdmin):
    """Class to handle NodeStatsAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + ("node",)


class ProgramAdmin(BaseAdmin):
    """Class to handle ProgramAdmin and functions."""

    inlines = [
        ProgramStatsInline,
    ]


admin.site.register(CITheme, ThemeAdmin)
admin.site.register(DashboardTheme, DashboardThemeAdmin)
admin.site.register(MenuItem, BaseAdmin)
admin.site.register(ConsumerInterfaceProduct, ConsumerInterfaceProductAdmin)
admin.site.register(ConsumerInterfaceStage, ConsumerInterfaceStageAdmin)
admin.site.register(NodeStats, NodeStatsAdmin)
admin.site.register(Program, ProgramAdmin)
admin.site.register(ProgramStat, BaseAdmin)
admin.site.register(ConsumerInterfaceActor, ConsumerInterfaceActorAdmin)
admin.site.register(ConsumerInterfaceClaim, ConsumerInterfaceClaimAdmin)
admin.site.register(ConsumerInterfaceClaimIntervention, ConsumerInterfaceClaimInterventionAdmin)
