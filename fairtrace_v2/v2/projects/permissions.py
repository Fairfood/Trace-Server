"""Permissions of the app projects."""
from common.exceptions import AccessForbidden
from common.exceptions import BadRequest
from common.library import _decode
from rest_framework import permissions

from .models import Project


class HasProjectAccess(permissions.BasePermission):
    """Check if the user is a member of the Node."""

    def has_permission(self, request, view):
        """Overriding permission check to check if the user is a member of the
        node."""
        node = view.kwargs["node"]
        project_id = _decode(request.META.get("HTTP_PROJECT_ID", None))
        if not project_id:
            raise BadRequest("Project ID is required")
        try:
            project = Project.objects.get(id=project_id)
        except Exception:
            raise BadRequest("invalid project id")
        if node not in project.member_nodes.all() and node != project.owner:
            raise AccessForbidden("Node does not have access to the project.")
        view.kwargs["project"] = project
        return True
