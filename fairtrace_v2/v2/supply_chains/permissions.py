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
        """
        Check if the user has permission to access the view.

        Args:
            request (HttpRequest): The request object.
            view (View): The view object.

        Returns:
            bool: True if the user has permission, False otherwise.

        Raises:
            BadRequest: If the node ID is missing and the user is not an admin.
            AccessForbidden: If the user does not have access to the node or 
            if an admin tries to access a node directly.

        """
        user = view.kwargs["user"]
        node_id = _decode(request.META.get("HTTP_NODE_ID", None))
        impersonate = request.META.get("HTTP_X_IMPERSONATE", None)

        # Check if the user is an admin
        admin = request.session.get("type") in {"ADMIN", "MANAGER"}

        if not admin and not node_id:
            raise BadRequest("Node ID is required")

        # Fetch the node from the database
        if node_id:
            node = Node.objects.get(pk=node_id)
        else:
            node = None

        # Check if impersonation is allowed only for admin users
        if (admin and impersonate == "true") or (admin and not node):
            view.kwargs["node"] = node
            return True

        # Check if the user is a member of the node
        member = NodeMember.objects.filter(node_id=node_id, user=user).first()

        if admin:
            raise AccessForbidden("Admin has no direct access to the node.")
        if not member:
            raise AccessForbidden("User does not have access to the node.")

        # Check if the user has access to the node @todo
        # if member.node.idencode not in request.session.get("nodes", []):
        #     raise AccessForbidden("User does not have access to the node.")

        # Make the member active and set the node in the view kwargs
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
        
        admin = request.session.get("type") in {"ADMIN", "MANAGER"} 

        if not node_id:
            raise BadRequest("Node ID is required")

        # fetch node from db
        node = Node.objects.get(pk=node_id)


        # checking impersonate is allowed.
        if admin and impersonate == "true":
            view.kwargs["node"] = node
            return True

        member = NodeMember.objects.filter(
            node_id=node_id,
            user=user,
            type__in=[NODE_MEMBER_TYPE_ADMIN, NODE_MEMBER_TYPE_MEMBER],
        ).first()

        if not member:
            raise AccessForbidden("User does not have access to the node.")
        else:
            if admin:
                raise AccessForbidden(
                    "Admin has no direct access to the node.")
        
        # if member.node.idencode not in request.session.get("nodes", []):
        #     raise AccessForbidden("User does not have access to the node.")
        
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

        admin = request.session.get("type") in {"ADMIN", "MANAGER"} 

        if not node_id:
            raise BadRequest("Node ID is missing in Header")

        # fetch node from db
        node = Node.objects.get(pk=node_id)

        # checking impersonate is allowed.
        if admin and impersonate == "true":
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
        
        if admin:
            raise AccessForbidden(
                "Admin has no direct access to the node.")
        
        if member.node.idencode not in request.session.get("nodes", []):
            raise AccessForbidden("User does not have access to the node.")

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
        # TODO: enebale this
        # if node.idencode not in request.session.get("nodes", []):
        #     raise AccessForbidden("User does not have access to the node.")
        return True


class IsFairfoodAdmin(permissions.BasePermission):
    """Check if the user is an admin of the fairfood."""

    def has_permission(self, request, view):
        """Overriding permission check to check if the user type is an admin of
        the fairfood."""
        
        admin = request.session.get("type") in {"ADMIN", "MANAGER"} 
        
        try:
            user = view.kwargs["user"]
            if not admin:
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
