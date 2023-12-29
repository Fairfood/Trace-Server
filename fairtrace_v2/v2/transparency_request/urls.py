"""URLs of the app transparency request."""
from django.urls import path

from .views import claim as claim_views
from .views import connection as conn_views
from .views import stock as stock_views
from .views import transparency as transparency_views

urlpatterns = [
    # Stock Requests
    path(
        "stock/",
        stock_views.StockRequestListCreateView.as_view(),
        name="stock",
    ),
    path(
        "stock/verify/",
        stock_views.StockRequestVerificationView.as_view(),
        name="stock-verify",
    ),
    path(
        "stock/<idencode:pk>/",
        stock_views.StockRequestRetrieveDestroyView.as_view(),
        name="stock-retrieve",
    ),
    # Claim Requests
    path("claim/", claim_views.ClaimRequestView.as_view(), name="claim"),
    path(
        "claim/<idencode:pk>/",
        claim_views.ClaimRequestDetails.as_view(),
        name="claim-details",
    ),
    path(
        "claim/<idencode:pk>/attach/",
        claim_views.AttachRequestedClaim.as_view(),
        name="claim-attach",
    ),
    path(
        "claim/field/<idencode:pk>/",
        claim_views.ClaimRequestFieldView.as_view(),
        name="claim-field",
    ),
    # Connection Requests
    path(
        "connection/",
        conn_views.ConnectionRequestView.as_view(),
        name="connection",
    ),
    path(
        "connection/<idencode:pk>/",
        conn_views.ConnectionRequestDetails.as_view(),
        name="connection-details",
    ),
    # Transparency Requests
    path(
        "",
        transparency_views.TransparencyRequestList.as_view(),
        name="transparency-request",
    ),
]
