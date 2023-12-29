# Register your models here.
from django.contrib import admin

from .library import format_json_readonly
from .models.callback_auth import CallBackToken
from .models.request import BlockchainRequest
from .models.request import CallbackResponse


# Register your models here.


def retry_request(modeladmin, request, queryset):
    """To perform function retry_request."""
    for item in queryset:
        item.retry()


retry_request.short_description = "Retry request"


class ResponseInline(admin.TabularInline):
    """Class to handle ResponseInline and functions."""

    def response(self, obj):
        """To format response json."""
        "response"
        return format_json_readonly(obj.data)

    model = CallbackResponse
    readonly_fields = ["created_on", "response", "success"]
    fields = ["response", "created_on", "success"]
    extra = 0


class CallBackTokenAdmin(admin.ModelAdmin):
    """Class to handle CallBackTokenAdmin and functions."""

    readonly_fields = ("idencode", "created_on", "updated_on")
    list_display = ("idencode", "key", "status")


class RequestAdmin(admin.ModelAdmin):
    """Class to handle RequestAdmin and functions."""

    def request_response(self, obj):
        """To format response json."""
        "request_response"
        return format_json_readonly(obj.response)

    def request_body(self, obj):
        """To format response json."""
        "request_response"
        return format_json_readonly(obj.body)

    readonly_fields = (
        "status",
        "created_on",
        "request_body",
        "request_response",
        "idencode",
        "updated_on",
        "creator",
        "receipt",
        "callback_token",
        "object_related_name",
        "password",
        "last_api_call",
    )
    exclude = ("type", "response", "body")
    list_display = (
        "__str__",
        "idencode",
        "status",
        "created_on",
        "last_api_call",
    )
    inlines = [
        ResponseInline,
    ]
    list_filter = ("type", "status", "created_on")

    actions = [retry_request]


admin.site.register(CallBackToken, CallBackTokenAdmin)
admin.site.register(CallbackResponse)
admin.site.register(BlockchainRequest, RequestAdmin)
for subclass in BlockchainRequest.__subclasses__():
    admin.site.register(subclass, RequestAdmin)
