"""URLs of the app dashboard."""
from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ci_theme
from .views import configuration
from .views import dash_theme
from .views import dashboard

router = DefaultRouter()
router.register(
    "ci-theme-language",
    ci_theme.CIThemeLanguageViewSet,
    base_name="ci-theme-language",
)

urlpatterns = [
    # Consumer Interface Theme APIs
    path("", include(router.urls)),
    path(
        "ci/theme/name/validate/",
        ci_theme.ValidateName.as_view(),
        name="ci-validate-name",
    ),
    path(
        "ci/theme/batch/validate/",
        ci_theme.ValidateBatch.as_view(),
        name="ci-validate-batch",
    ),
    path(
        "ci/theme/", ci_theme.CIThemeListCreateAPI.as_view(), name="ci-theme"
    ),
    path(
        "ci/theme/<slug:pk>/",
        ci_theme.CIThemeRetrieveUpdateDestroyAPI.as_view(),
        name="ci-theme-retrieve",
    ),
    path("ci/product/", ci_theme.CreateCIProduct.as_view(), name="ci-product"),
    path(
        "ci/product/<idencode:pk>/",
        ci_theme.RetrieveUpdateDeleteCIProduct.as_view(),
        name="ci-product-retrieve",
    ),
    path("ci/stage/", ci_theme.CreateCIStage.as_view(), name="ci-stage"),
    path(
        "ci/stage/<idencode:pk>/",
        ci_theme.RetrieveUpdateDeleteCIStage.as_view(),
        name="ci-stage-retrieve",
    ),
    path(
        "ci/menu_item/",
        ci_theme.CreateCIMenuItem.as_view(),
        name="ci-menu-item",
    ),
    path(
        "ci/menu_item/<idencode:pk>/",
        ci_theme.RetrieveUpdateDeleteCIMenuItem.as_view(),
        name="ci-menu-item-retrieve",
    ),
    # Dashboard themes
    path("theme/", dash_theme.NodeDashboardThemeView.as_view(), name="theme"),
    path(
        "admin/theme/",
        dash_theme.FFAdminDashboardThemeView.as_view(),
        name="admin-theme",
    ),
    path(
        "admin/theme/<slug:pk>/",
        dash_theme.FFAdminDashboardThemeDetailsView.as_view(),
        name="admin-theme-retrieve",
    ),
    # Dashboard APIs
    path("stats/", dashboard.StatsView.as_view(), name="stats"),
    # Configurations
    path("config/", configuration.ConfigurationsView.as_view(), name="config"),
    # API used from the consumer interface. Public API with only OTP
    # authentication
    path(
        "public/theme/<slug:name>/",
        ci_theme.PublicThemeDetails.as_view(),
        name="public-theme",
    ),
]
