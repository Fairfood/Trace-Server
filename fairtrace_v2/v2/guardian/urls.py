from django.urls import path, include
from v2.guardian.views import CheckClaimStatusView


urlpatterns = [
    path("claim-status/", view=CheckClaimStatusView.as_view())
]