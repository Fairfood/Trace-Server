"""URLs of the app accounts."""
from django.urls import path

from . import views

urlpatterns = [
    path("hash/", views.UpdateBlockchainHashAPI.as_view(), name="update-hash"),
]
