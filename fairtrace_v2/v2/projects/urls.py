"""URLs of the app projects."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from v2.projects.views import nodes, products, projects, public, transactions

router = DefaultRouter()
router.register("payments", projects.PaymentViewSet, basename="payments")
router.register(
    "premiums", projects.ProjectPremiumViewSet, basename="premiums"
)


urlpatterns = [
    path(
        "project/<idencode:pk>/",
        projects.ProjectDetailsAPI.as_view(),
        name="project-details",
    ),
    path(
        "project/<idencode:pk>/product/",
        products.ProjectProductListAPI.as_view(),
        name="project-product-list",
    ),
    path(
        "project/<idencode:pk>/supplier/",
        nodes.ProjectSupplierListAPI.as_view(),
        name="project-supplier-list",
    ),
    path(
        "project/<idencode:pk>/buyer/",
        nodes.ProjectBuyerListAPI.as_view(),
        name="project-buyer-list",
    ),
    path("sms/", public.SMSBalanceAPIView.as_view()),
    path("whatsapp-webhook/<lan>/", public.WhatsAppWebHookView.as_view()),
    path(
        "farmer/invite/",
        nodes.FarmerInviteAPI.as_view(),
        name="add-farmer-to-project",
    ),
    path(
        "farmer/<idencode:pk>/",
        nodes.FarmerDetails.as_view(),
        name="get-update-farmer",
    ),
    path("card/", projects.CardAPI.as_view(), name="list-create-card"),
    path(
        "transaction/",
        transactions.AppTransactionAPI.as_view(),
        name="create-list-transaction",
    ),
    path("transaction-sent/", transactions.AppSentTransactionAPI.as_view()),
    path(
        "transaction/list/",
        transactions.AppTransactionListAPI.as_view(),
        name="create-list-transaction",
    ),
    path(
        "transaction/<idencode:pk>/invoice/",
        transactions.TransactionInvoiceAPI.as_view(),
        name="update-transaction-invoice",
    ),
    path("open/farmer/<pk>/", nodes.FarmerDetailsAPI.as_view()),
    path("open/transaction/", transactions.OpenTransactionAPI.as_view()),
    path(
        "open/transaction/<pk>/", transactions.OpenTransactionDetails.as_view()
    ),
    path("batch/details/", transactions.AppBatchDetails.as_view()),
    path("login/", projects.AppLogin.as_view()),
    path(
        "logout/",
        projects.AppLogout.as_view(),
    ),
    path("final-sync/", projects.FanalSyncView.as_view()),
    path("reverse-sync/", projects.ReverseSynchView.as_view()),
    path("navigate-sync/", projects.NavigateSynchView.as_view()),
    path('migrate-connect/', projects.migrate_connect,name='migrate_connect'),
    path("projects/", include(router.urls)),
]
