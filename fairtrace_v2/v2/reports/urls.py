from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter
from v2.reports.views import ExportViewSet

router = DefaultRouter()

router.register("exports", ExportViewSet, basename="exports")

urlpatterns = [path("", include(router.urls))]
