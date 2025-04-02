"""Admin file of the app accounts."""
from common.admin import BaseAdmin
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from v2.supply_chains.models import Node

from .models import AccessToken
from .models import ClientVersion
from .models import FairfoodUser
from .models import Person
from .models import TermsAndConditions
from .models import UserClientVersion
from .models import UserDevice
from .models import UserTCAcceptance
from .models import ValidationToken

environment = settings.ENVIRONMENT.capitalize()
admin.site.site_header = "%s Fairfood Admin" % environment
admin.site.site_title = "Fairfood: %s Admin Portal" % (environment)
admin.site.index_title = "Welcome to Fairfood %s Portal" % (environment)


class NodeInline(admin.TabularInline):
    """In-line view function for Sub-element model."""

    model = Node.members.through
    extra = 0
    fk_name = "user"
    can_delete = False
    show_change_link = False

    fields = ("node", "active", "type")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        """To perform function has_add_permission."""
        return False


class ValidationTokenAdmin(admin.ModelAdmin):
    """Class view to customize validation token admin."""

    ordering = ("-updated_on",)

    def salt(self, obj):
        """Get salt."""
        return obj.idencode

    list_display = ("user", "key", "status", "salt", "type", "expiry")
    list_filter = ("type", "status")


class AccessTokenAdmin(admin.ModelAdmin):
    """Class view to customize validation token admin."""

    def email(self, obj):
        """Show email in list."""
        return obj.user.email

    list_display = ("user", "email", "key")


class UserDeviceAdmin(admin.ModelAdmin):
    """Class view to customize user device admin."""

    list_display = ("user", "device_id", "registration_id", "type")


class AccessTokenInline(admin.TabularInline):
    """In-line view function for SourceBatch."""

    def get_user_id(self, obj):
        """To perform function get_user_id."""
        return obj.user.idencode

    readonly_fields = ("get_user_id", "key", "created")
    model = AccessToken
    extra = 0
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        """To perform function has_add_permission."""
        return False


class FairfoodUserAdmin(UserAdmin):
    """Overriding user adminto add additional fields."""

    readonly_fields = ("idencode", "default_node")
    ordering = ("-id",)
    inlines = [
        AccessTokenInline,
        NodeInline,
    ]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "updated_email",
                    "dob",
                    "phone",
                    "address",
                    "language",
                    "image",
                    "idencode",
                    "external_id"
                )
            },
        ),
        (
            "Internal values",
            {
                "fields": (
                    "type",
                    "status",
                    "terms_accepted",
                    "privacy_accepted",
                    "email_verified",
                ),
            },
        ),
        (
            "Node details",
            {
                "fields": ("default_node",),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    list_display = (
        "idencode",
        "first_name",
        "last_name",
        "email",
        "email_verified",
        "external_id"
    )


admin.site.register(FairfoodUser, FairfoodUserAdmin)
admin.site.register(UserDevice, UserDeviceAdmin)
admin.site.register(AccessToken, AccessTokenAdmin)
admin.site.register(ValidationToken, ValidationTokenAdmin)
admin.site.register(Person)
admin.site.register(TermsAndConditions)
admin.site.register(UserTCAcceptance)
admin.site.register(ClientVersion, BaseAdmin)
admin.site.register(UserClientVersion, BaseAdmin)
