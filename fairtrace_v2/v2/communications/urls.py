"""URLs of the app tasks."""
from django.urls import path

from .views.notification import NotificationDetails
from .views.notification import NotificationList
from .views.notification import ReadNotification

urlpatterns = [
    # Notification APIS
    path("notifications/", NotificationList.as_view(), name="notifications"),
    path(
        "notifications/read/",
        ReadNotification.as_view(),
        name="notifications-read",
    ),
    path(
        "notifications/<idencode:pk>/",
        NotificationDetails.as_view(),
        name="notifications-details",
    ),
]
