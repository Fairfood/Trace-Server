"""Views related to notifications are defined here."""
from common.library import _decode_list, decode, encode
from common.library import _success_response
from django.core.exceptions import ValidationError
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework import viewsets
from v2.supply_chains.models.node import Node
from v2.communications.constants import STOPABLE_NOTIFICATIONS
from v2.accounts import permissions as user_permissions
from v2.communications.filters import NotificationFilter
from v2.communications.models import EmailConfiguration, Notification
from v2.communications.serializers.notification import NotificationSerializer


# /communications/notifications/
class NotificationList(generics.ListAPIView):
    """View to list notification list."""

    http_method_names = ["get"]
    serializer_class = NotificationSerializer
    permission_classes = (user_permissions.IsAuthenticatedWithVerifiedEmail,)
    filterset_class = NotificationFilter

    def get_queryset(self):
        """To override get query set."""
        queryset = Notification.objects.filter(
            user=self.kwargs["user"], visibility=True
        )
        return queryset

    def list(self, request, *args, **kwargs):
        """Overriding response to add unread count."""
        response = super().list(request, args, kwargs)
        queryset = self.filter_queryset(self.get_queryset())
        response.data["unread"] = queryset.filter(is_read=False).count()
        return response


# /communications/notifications/<idencode>/
class NotificationDetails(generics.RetrieveAPIView):
    """View to list notification list."""

    serializer_class = NotificationSerializer
    # permission_classes = (
    #     user_permissions.IsAuthenticated,
    # )
    filterset_class = NotificationFilter
    queryset = Notification.objects.all()

    # def get_queryset(self):
    #     """To override get query set."""
    #     queryset = Notification.objects.filter(
    #         user=self.kwargs['user'], visibility=True)
    #     return queryset


# /communications/notifications/read/
class ReadNotification(APIView):
    """View to read notifications."""

    http_method_names = ["patch"]

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        # user_permissions.IsAccountApproved
    )

    @staticmethod
    def patch(request, user=None, *args, **kwargs):
        """Function to read notifications.

        Input Params:
            kwargs:
                account(obj): account object from IsAuthenticated
                    decorator.
            Request Body Params:
                ids(list): List of encoded ids of notifications
        Response:
            Success response.
        """
        data = request.data
        ids = []
        if "ids" in data.keys():
            ids = _decode_list(data["ids"])

        notifications = Notification.objects.filter(user=user)

        if "all" not in data or not data["all"]:
            notifications = notifications.filter(id__in=ids)

        for notification in notifications:
            notification.read()

        return _success_response({}, "Notifications read successfully.", 200)


class EmailConfigurationViewSet(viewsets.ViewSet):

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
    )

    def list(self, request, *args, **kwargs):
        """List all the email configurations."""
        node = self.request.query_params.get("node", None)
        user = request.user
        if not node:
            nodes = Node.objects.filter(nodemembers__user=user).distinct()
        else:
            nodes = Node.objects.filter(id=decode(node))
        
        queryset = EmailConfiguration.objects.filter(
            user=user, type__in=STOPABLE_NOTIFICATIONS)
        

        data = []
        for node in nodes:
            data.extend(self.get_node_notifiactions(node, queryset, user))
    
        return _success_response(data)

    
    def create(self, request, *args, **kwargs):
        """Create an email configuration."""
        user = request.user

        if not isinstance(request.data, list):
            return _success_response(
                {}, "Invalid request data.", 400)
        
        for data in request.data:
            _type = data.get("type", None)
            is_blocked = data.get("is_blocked", False)
            node = data.get("node", None)
            node = self.validate_node(node, user)

            if _type:
                _type = int(_type)
            
            if _type not in STOPABLE_NOTIFICATIONS:
                return _success_response(
                    {}, f"Invalid type {_type}.", 400)
            self.create_config(_type, node, is_blocked, user)
        
        return _success_response(
            {}, "Email configuration created successfully.", 201)
    
    def validate_node(self, node, user):
        """Validate the node."""
        try:
            node = Node.objects.get(id=decode(node))
        except Node.DoesNotExist:
            raise ValidationError(f"Node {node} does not exist.")
        
        if not user.usernodes.filter(node=node).exists():
            raise ValidationError(
                f"User does not have access to this node {node}.")
        
        return node
    
    def create_config(self, _type, node, is_blocked, user):
        """Create email configuration."""
        email_config, _ = EmailConfiguration.objects.get_or_create(
            node=node, type=_type, user=user)
        email_config.is_blocked = is_blocked
        email_config.save()

    def get_node_notifiactions(self, node, queryset, user):
        """
        Get node notifications.
        """
        if not user.usernodes.filter(node=node).exists():
            return ValidationError(
                f"User does not have access to this node {node}.")
        
        queryset = queryset.filter(node=node)
        data = [
            {
            "node": encode(config["node"]), 
            "type": config["type"], 
            "is_blocked": config["is_blocked"]
            } 
            for config in queryset.values("node", "type", "is_blocked")
            ]
        
        grouped_qs = dict(map(lambda x: (x["type"], x), data))
        
        for _type in STOPABLE_NOTIFICATIONS:
            if _type not in grouped_qs:
                grouped_qs[_type] = {
                    "node": node.idencode,
                    "type": _type,
                    "is_blocked": False
                }
        return list(grouped_qs.values())
            
        