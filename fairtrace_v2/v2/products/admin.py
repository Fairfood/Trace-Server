from common.admin import BaseAdmin
from common.library import decode
from django.contrib import admin
from v2.dashboard import cache_handlers
from v2.products.models import Batch
from v2.products.models import BatchFarmerMapping
from v2.products.models import BatchMigration
from v2.products.models import Product


# from v2.products.models import BatchComment

# Register your models here.


def create_token(modeladmin, request, queryset):
    """To perform function create_token."""
    for item in queryset:
        item.create_token()


def clear_filesystem_cache(modeladmin, request, queryset):
    """To perform function clear_filesystem_cache."""
    if queryset.count() > 10:
        raise Exception("Select less than 10 items")
    for item in queryset:
        cache_handlers.clear_ci_map_cache.delay(item.id, ignore_parents=True)
        cache_handlers.clear_ci_stage_cache.delay(item.id, ignore_parents=True)
        cache_handlers.clear_ci_claim_cache.delay(item.id, ignore_parents=True)


create_token.short_description = "Create Hedera Token"


class ProductAdmin(BaseAdmin):
    """Class to handle ProductAdmin and functions."""

    list_display = ("name", "idencode", "supply_chain", "type")
    list_filter = ("supply_chain", "type")
    list_select_related = ("supply_chain",)
    search_fields = ["name"]
    actions = [create_token]


class BatchAdmin(BaseAdmin):
    """Class to handle BatchAdmin and functions."""

    list_display = (
        "product",
        "name",
        "node",
        "idencode",
        "initial_quantity",
        "current_quantity",
        "created_on",
    )
    readonly_fields = (
        "source_transaction",
        "creator",
        "updater",
        "node_wallet",
        "block_chain_request",
        "submit_message_request",
    )
    list_select_related = ("node", "node__company", "node__farmer", "product")
    actions = [clear_filesystem_cache]
    search_fields = ("product__name",)
    autocomplete_fields = ("node", "source_transaction", "product")

    def get_search_results(self, request, queryset, search_term):
        """For searching with idencode."""
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        pk = decode(search_term)
        if pk:
            queryset |= self.model.objects.filter(pk=pk)

        return queryset, use_distinct


class BatchMigrationAdmin(BaseAdmin):
    """Class to handle BatchMigrationAdmin and functions."""

    def get_readonly_fields(self, request, obj=None):
        """To perform function get_readonly_fields."""
        return list(
            set(
                [field.name for field in self.opts.local_fields]
                + [field.name for field in self.opts.local_many_to_many]
            )
        )


class BatchFarmerMappingAdmin(BaseAdmin):
    """Class to handle BatchFarmerMappingAdmin and functions."""

    pass


admin.site.register(Product, ProductAdmin)
admin.site.register(Batch, BatchAdmin)
admin.site.register(BatchMigration, BatchMigrationAdmin)
admin.site.register(BatchFarmerMapping, BatchFarmerMappingAdmin)
# admin.site.register(BatchComment)
