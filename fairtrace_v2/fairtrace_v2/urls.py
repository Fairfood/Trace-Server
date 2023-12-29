"""Fairtrace_v2 URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import debug_toolbar
from common.drf_custom import converters
from django.conf import settings
from django.conf.urls import include
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.urls import register_converter
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

register_converter(converters.IDConverter, "idencode")

# if settings.ENVIRONMENT == 'production':
#     from django_otp.admin import OTPAdminSite
#     admin.site.__class__ = OTPAdminSite

schema_view = get_schema_view(
    openapi.Info(
        title="Fairtrace V2 API",
        default_version="v2",
        description="APIs availabe for Fairtrace V2",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("djadmin-ff/", admin.site.urls),
    path("__debug__/", include(debug_toolbar.urls)),
    url(r"^nested_admin/", include("nested_admin.urls")),
    url("v2/blockchain/", include("v2.blockchain.urls")),
    url("v2/accounts/", include("v2.accounts.urls")),
    url("v2/communications/", include("v2.communications.urls")),
    url("v2/supply-chain/", include("v2.supply_chains.urls")),
    url("v2/products/", include("v2.products.urls")),
    url("v2/transactions/", include("v2.transactions.urls")),
    url("v2/claims/", include("v2.claims.urls")),
    url("v2/dashboard/", include("v2.dashboard.urls")),
    url("v2/activity/", include("v2.activity.urls")),
    url("v2/requests/", include("v2.transparency_request.urls")),
    url("v2/projects/", include("v2.projects.urls")),
    url("v2/reports/", include("v2.reports.urls")),
    url("v2/bulk_templates/", include("v2.bulk_templates.urls")),
    url("v2/bulk-uploads/", include("v2.bulk_uploads.urls")),
    url(r"^djadmin-ff/scripts/", include("scripts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns += [
        url(
            r"^doc/$",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
    ]
