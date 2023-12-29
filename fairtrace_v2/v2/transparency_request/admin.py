from common.admin import BaseAdmin
from django.contrib import admin

from .models import ClaimRequest
from .models import ClaimRequestField
from .models import ConnectionRequest
from .models import StockRequest
from .models import StockRequestClaim


# Register your models here.


class StockRequestAdmin(BaseAdmin):
    """Class to handle StockRequestAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + (
        "claims",
        "transaction",
        "requester",
        "requestee",
        "connection",
        "product",
    )
    list_display = BaseAdmin.list_display + ("product", "status", "deleted")
    list_select_related = (
        "product",
        "requester",
        "requester__farmer",
        "requester__company",
        "requestee",
        "requestee__farmer",
        "requestee__company",
    )


class StockRequestClaimAdmin(BaseAdmin):
    """Class to handle StockRequestClaimAdmin and functions."""

    pass


class ClaimRequestAdmin(BaseAdmin):
    """Class to handle ClaimRequestAdmin and functions."""

    pass


class ClaimRequestFieldAdmin(BaseAdmin):
    """Class to handle ClaimRequestFieldAdmin and functions."""

    pass


class ConnectionRequestAdmin(BaseAdmin):
    """Class to handle ConnectionRequestAdmin and functions."""

    pass


admin.site.register(StockRequest, StockRequestAdmin)
admin.site.register(StockRequestClaim, StockRequestClaimAdmin)
admin.site.register(ClaimRequest, ClaimRequestAdmin)
admin.site.register(ClaimRequestField, ClaimRequestFieldAdmin)
admin.site.register(ConnectionRequest, ConnectionRequestAdmin)
