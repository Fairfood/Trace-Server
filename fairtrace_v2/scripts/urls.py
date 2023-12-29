from django.urls import path

from .views import CopySupplyChainView

urlpatterns = [
    path("copy-supplychain/", CopySupplyChainView.as_view(), name="copy_sc"),
]
