"""URLs of the app accounts."""
from django.urls import path

from .views import activity as activity_views

urlpatterns = [
    # Activity views
    path("node/", activity_views.NodeActivity.as_view(), name="node-activity"),
    path("user/", activity_views.UserActivity.as_view(), name="user-activity"),
]
