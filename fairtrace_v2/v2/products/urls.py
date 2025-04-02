"""URLs of the products in products app."""
from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import batch as batch_views
from .views import product as product_views
from .views import trace as trace_views
from .views import transaction_report as report_views

router = DefaultRouter()
router.register(
    "batch-farmers",
    batch_views.BatchFarmerMappingViewSet,
    base_name="batch-farmers",
)

urlpatterns = [
    # Product
    path("", product_views.ProductView.as_view(), name="product"),
    path(
        "bulk/", product_views.BulkCreateProduct.as_view(), name="bulk-product"
    ),
    path("verification/", product_views.ProductListView.as_view()),
    # Batch
    path("batch/", batch_views.BatchList.as_view(), name="batch"),
    path("batch/toggle-archive/", batch_views.BatchArchiveView.as_view(), name="toggle-archive"),
    path("batch-summary/", batch_views.BatchSummary.as_view(), 
         name="batch-summary"),
    path(
        "batch/<idencode:pk>/",
        batch_views.BatchDetails.as_view(),
        name="batch-details",
    ),
    # path('batch/comment/', batch_views.BatchCommentView.as_view()),
    # Consumer Interface
    path(
        "batch/<idencode:pk>/trace/",
        trace_views.TraceBatch.as_view(),
        name="batch-trace",
    ),
    path(
        "claim/<idencode:pk>/trace/",
        trace_views.TraceClaimWithBatch.as_view(),
        name="claim-trace",
    ),
    path(
        "map/<idencode:pk>/trace/",
        trace_views.TraceMap.as_view(),
        name="map-trace",
    ),
    path(
        "stage/<idencode:pk>/trace/",
        trace_views.TraceStagesWithBatch.as_view(),
        name="stage-trace",
    ),
    path(
        "transaction/<idencode:pk>/trace/",
        trace_views.TraceTransactionsWithBatchActor.as_view(),
        name="transaction-trace",
    ),
    path("batches/", include(router.urls)),
    # Transaction report
    path(
        "claim/<idencode:pk>/report/",
        report_views.TraceClaimWithBatchForReport.as_view(),
        name="claim-report",
    ),
    path(
        "map/<idencode:pk>/report/",
        report_views.TraceMapForReport.as_view(),
        name="map-report",
    ),
    path(
        "stage/<idencode:pk>/report/",
        report_views.TraceStagesWithBatchForReport.as_view(),
        name="stage-report",
    ),
    path(
        "transaction/<idencode:pk>/report/",
        report_views.TraceTransactionsWithBatchActorForReport.as_view(),
        name="transaction-report",
    ),
]
