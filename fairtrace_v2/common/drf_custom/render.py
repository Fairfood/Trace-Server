"""Custom render class to custom success response."""
from rest_framework.renderers import JSONRenderer


class ApiRenderer(JSONRenderer):
    """Custom render class."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """Custom render function."""
        response_data = data
        try:
            if not data["success"]:
                response_data = data
        except Exception:
            response_data = {
                "success": True,
                "detail": "Success",
                "code": renderer_context["response"].status_code,
                "data": data,
            }
        try:
            getattr(
                renderer_context.get("view").get_serializer().Meta,
                "resource_name",
                "objects",
            )
        except Exception:
            pass

        response = super(ApiRenderer, self).render(
            response_data, accepted_media_type, renderer_context
        )

        return response
