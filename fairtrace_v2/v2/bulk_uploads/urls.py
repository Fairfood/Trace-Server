"""URLs of the app bulk_templates."""
from django.conf.urls import include
from django.urls import path
from rest_framework import routers
from v2.bulk_uploads.views import templates as template_views
from v2.bulk_uploads.views import uploads as upload_views

router = routers.DefaultRouter()
router.register(
    r"data-sheet-templates",
    template_views.DataSheetTemplateViewSet,
    basename="data-sheet-templates",
)
router.register(
    r"data-sheet-uploads",
    upload_views.DataSheetUploadViewSet,
    basename="data-sheet-uploads",
)

urlpatterns = [path("", include(router.urls))]
