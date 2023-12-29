"""Permissions of the app bulk_templates."""
from common import library as comm_lib
from common.exceptions import AccessForbidden
from common.exceptions import BadRequest
from rest_framework import permissions
from v2.bulk_templates import models as temp_models


class HasTemplateAccess(permissions.BasePermission):
    """Checks if the base node and template node are the same.

    and thereby the user has access to the object node.
    """

    def has_permission(self, request, view):
        """To perform function has_permission."""
        base_node = view.kwargs["node"]
        template_id = view.kwargs.get("pk", None)
        if not template_id:
            raise BadRequest("Template ID is required in the URL.")
        template = temp_models.Template.objects.get(
            id=comm_lib._decode(template_id)
        )
        if base_node not in template.nodes.all():
            raise AccessForbidden("Access denied to the Node")
        return True
