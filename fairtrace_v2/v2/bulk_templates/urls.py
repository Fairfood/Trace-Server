"""URLs of the app bulk_templates."""
from django.conf.urls import include
from django.urls import path
from rest_framework import routers
from v2.bulk_templates import models as temp_models
from v2.bulk_templates.views import templates

router = routers.SimpleRouter()
router.register(r"", templates.TemplateViewSet, basename=temp_models.Template)
router.register(
    r"bulk-create",
    templates.DynamicUploadViewSet,
    basename=temp_models.DynamicBulkUpload,
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "fields/<type>/",
        templates.TemplateFieldList.as_view(),
        name="template-field-type",
    ),
]
