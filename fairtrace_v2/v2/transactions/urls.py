"""URLs of the app transactions."""
from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import admin_dashboard_v3 as ff_admin_views_v3
from .views import transactions as trans_views
from .views import carbon_transactions as carbon_views


router = DefaultRouter()
router.register(
    "external-transactions",
    ff_admin_views_v3.AdminExternalTransactionViewSet,
    base_name="external-transactions",
)
router.register(
    "external-transaction-count",
    ff_admin_views_v3.AdminExternalTransactionCountViewSet,
    base_name="external-transaction-count",
)
router.register(
    "external-transaction-quantity",
    ff_admin_views_v3.AdminExternalTransactionQuantityViewSet,
    base_name="external-transaction-quantity",
)
router.register(
    "stats", ff_admin_views_v3.AdminStatisticsViewSet, base_name="stats"
)

router_2 = DefaultRouter()
router_2.register(
    "transaction-attachments",
    trans_views.TransactionAttachmentViewSet,
    base_name="transaction-attachments",
)

urlpatterns = [
    path(
        "external/",
        trans_views.ExternalTransactionView.as_view(),
        name="external",
    ),
    # path('external/bulk/',
    #      trans_views.CreateBulkExternalTransaction.as_view(),
    #      name='external-bulk'),
    path(
        "external/<idencode:pk>/",
        trans_views.ExternalTransactionDetails.as_view(),
        name="external-details",
    ),
    path(
        "external/toggle-archive/",
        trans_views.ExtenalTransactionArchiveView.as_view(),
        name="external-transaction-toggle-archive",
    ),
    
    path(
        "internal/toggle-archive/",
        trans_views.InternalTransactionArchiveView.as_view(),
        name="internal-transaction-toggle-archive",
    ),
    path(
        "external/<idencode:pk>/reject/",
        trans_views.RejectExternalTransaction.as_view(),
        name="external-reject",
    ),
    path(
        "bulk/external/",
        trans_views.BulkTransactionTemplate.as_view(),
        name="bulk-transaction-template",
    ),
    path(
        "bulk/external2/",
        trans_views.BulkTransactionTemplate2.as_view(),
        name="bulk-transaction-template",
    ),
    path(
        "internal/",
        trans_views.InternalTransactionView.as_view(),
        name="internal",
    ),
    path(
        "internal/<idencode:pk>/",
        trans_views.InternalTransactionDetails.as_view(),
        name="internal-details",
    ),
    path(
        "validate/transaction/",
        trans_views.ValidateTransaction.as_view(),
        name="internal-details",
    ),
    path(
        "validate/dynamic-transaction/",
        trans_views.ValidateDynamicTransaction.as_view(),
        name="validate_duplicate_txn",
    ),
    path(
        "carbon-external/", 
        carbon_views.CarbonExternalTransactionView.as_view(),
        name="carbon-external"
    ),
    path(
        "carbon-internal/", 
        carbon_views.CarbonInternalTransactionView.as_view(),
        name="carbon-internal"
    ),
    path(
        "carbon-transactions/", 
        carbon_views.CarbonTransactionsView.as_view(),
        name="carbon-transactions"
    ),
    path("", include(router_2.urls)),
    # FF-Admin V3
    path("admin/", include(router.urls)),
]
