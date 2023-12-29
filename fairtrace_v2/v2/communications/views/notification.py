"""Views related to notifications are defined here."""
from common.library import _decode_list
from common.library import _success_response
from rest_framework import generics
from rest_framework.views import APIView
from v2.accounts import permissions as user_permissions
from v2.communications.filters import NotificationFilter
from v2.communications.models import Notification
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
