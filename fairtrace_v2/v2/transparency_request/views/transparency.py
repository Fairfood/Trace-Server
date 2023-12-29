"""Views for claim request related urls."""
from rest_framework import generics
from v2.accounts import permissions as user_permissions
from v2.supply_chains import permissions as sc_permissions
from v2.transparency_request.filters import TransparencyRequestFilter
from v2.transparency_request.models import TransparencyRequest
from v2.transparency_request.serializers import (
    transparency as trans_serializers,
)


class TransparencyRequestList(generics.ListAPIView):
    """Class to list transparency request."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = trans_serializers.TransparencyRequestSerializer
    filterset_class = TransparencyRequestFilter
    queryset = TransparencyRequest.objects.all().order_by("-id")
