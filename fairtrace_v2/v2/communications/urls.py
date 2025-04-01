"""URLs of the app tasks."""
from django.urls import path
from rest_framework.routers import DefaultRouter


from .views.notification import NotificationDetails
from .views.notification import NotificationList
from .views.notification import ReadNotification
from .views.notification import EmailConfigurationViewSet

router = DefaultRouter()
router.register(
    "email-configs", EmailConfigurationViewSet, base_name="email-configs"
)

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

urlpatterns += router.urls
