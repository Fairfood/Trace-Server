"""Permissions of the app supply_chains."""
from common.exceptions import AccessForbidden
from common.exceptions import BadRequest
from common.library import _decode
from rest_framework import permissions
from v2.accounts.constants import USER_TYPE_FAIRFOOD_ADMIN
from v2.accounts.constants import USER_TYPE_FAIRFOOD_MANAGER

from .constants import NODE_MEMBER_TYPE_ADMIN
from .constants import NODE_MEMBER_TYPE_MEMBER
from .models import Node
from .models import NodeMember


class HasNodeAccess(permissions.BasePermission):
    """Check if the user is a member of the Node."""

    def has_permission(self, request, view):
        """Overriding permission check to check if the user is a member of the
        node."""
        user = view.kwargs["user"]
        node_id = _decode(request.META.get("HTTP_NODE_ID", None))
        impersonate = request.META.get("HTTP_X_IMPERSONATE", None)
        if not user.is_fairtrace_admin:
            if not node_id:
                raise BadRequest("Node ID is required")

        # fetch node from db
        if node_id:
            node = Node.objects.get(pk=node_id)
        else:
            node = None

        # checking impersonate is allowed only for admin user.
        if user.is_fairtrace_admin:
            if impersonate == "true":
                view.kwargs["node"] = node
                return True

        member = NodeMember.objects.filter(node_id=node_id, user=user).first()

        if not member and not user.is_fairtrace_admin:
            raise AccessForbidden("User does not have access to the node.")
        if member:
            member.node.make_member_active(user)
        view.kwargs["node"] = node
        return True


class HasNodeWriteAccess(permissions.BasePermission):
    """Check if the user is a member of the Node."""

    def has_permission(self, request, view):
        """Overriding permission check to check if the user is a member of the
        node."""
        user = view.kwargs["user"]
        node_id = _decode(request.META.get("HTTP_NODE_ID", None))
        impersonate = request.META.get("HTTP_X_IMPERSONATE", None)
        if not node_id:
            raise BadRequest("Node ID is required")

        # fetch node from db
        node = Node.objects.get(pk=node_id)

        # checking impersonate is allowed.
        if user.is_fairtrace_admin and impersonate == "true":
            view.kwargs["node"] = node
            return True

        member = NodeMember.objects.filter(
            node_id=node_id,
            user=user,
            type__in=[NODE_MEMBER_TYPE_ADMIN, NODE_MEMBER_TYPE_MEMBER],
        ).first()

        if not member and not user.is_fairtrace_admin:
            raise AccessForbidden("User does not have access to the node.")
        if member:
            member.node.make_member_active(user)

        view.kwargs["node"] = node
        return True


class HasNodeAdminAccess(permissions.BasePermission):
    """Check if the user is an admin of the Node."""

    def has_permission(self, request, view):
        """Overriding permission check to check if the user is an admin of the
        node."""
        user = view.kwargs["user"]
        node_id = _decode(request.META.get("HTTP_NODE_ID", None))
        impersonate = request.META.get("HTTP_X_IMPERSONATE", None)
        if not node_id:
            raise BadRequest("Node ID is missing in Header")

        # fetch node from db
        node = Node.objects.get(pk=node_id)

        # checking impersonate is allowed.
        if user.is_fairtrace_admin and impersonate == "true":
            view.kwargs["node"] = node
            return True
        try:
            member = NodeMember.objects.get(
                node_id=node_id, user=user, type=NODE_MEMBER_TYPE_ADMIN
            )
        except Exception as e:
            raise AccessForbidden(
                f"You need to be Admin of the Node to perform this action.{e}"
            )

        member.node.make_member_active(user)
        view.kwargs["node"] = node
        return True


class HasIndirectNodeAccess(permissions.BasePermission):
    """Checks if the base node is the manager of the object node and thereby
    the user has access to the object node.

    This can only be used in conjunction with HasNodeAdminAccess or
    HasNodeAccess
    """

    def has_permission(self, request, view):
        """Check user has permission."""
        base_node = view.kwargs["node"]
        obj_node_id = view.kwargs.get("pk", None)
        if not obj_node_id:
            raise BadRequest("Node ID is required in the URL.")
        node = Node.objects.get(id=obj_node_id)
        if base_node not in node.managers.all() and node != base_node:
            raise AccessForbidden("Access denied to the Node")
        return True


class IsFairfoodAdmin(permissions.BasePermission):
    """Check if the user is an admin of the fairfood."""

    def has_permission(self, request, view):
        """Overriding permission check to check if the user type is an admin of
        the fairfood."""

        try:
            user = view.kwargs["user"]
            if user.type not in (
                USER_TYPE_FAIRFOOD_ADMIN,
                USER_TYPE_FAIRFOOD_MANAGER,
            ):
                raise AccessForbidden(
                    "You need to be Admin of the fairfood to perform this"
                    " action."
                )
        except Exception:
            raise AccessForbidden(
                "You need to be Admin of the fairfood to perform this action."
            )
        return True


class HasNodeAccessOrIsFairfoodAdmin(IsFairfoodAdmin, HasNodeAccess):
    """Check if either user is an admin of a node."""

    def has_permission(self, request, view):
        """Check both permissions."""
        try:
            check = HasNodeAccess().has_permission(request, view)
            if check:
                return True
        except Exception:
            pass
        return IsFairfoodAdmin().has_permission(request, view)
