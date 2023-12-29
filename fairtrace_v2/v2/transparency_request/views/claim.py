"""Views for claim request related urls."""
from common import library as comm_lib
from common.drf_custom.views import MultiPermissionView
from common.exceptions import BadRequest
from django.db.models import Q
from rest_framework import generics
from rest_framework.views import APIView
from v2.accounts import permissions as user_permissions
from v2.supply_chains import permissions as sc_permissions
from v2.transparency_request.models import ClaimRequest
from v2.transparency_request.models import ClaimRequestField
from v2.transparency_request.serializers import claim as claimreq_serializers


class ClaimRequestView(generics.CreateAPIView):
    """API to create claim requests."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = claimreq_serializers.ClaimRequestSerializer


class ClaimRequestDetails(generics.RetrieveUpdateAPIView, MultiPermissionView):
    """API to list claim requests details."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "PATCH": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
    }

    serializer_class = claimreq_serializers.ClaimRequestSerializer

    def get_queryset(self):
        """Filter qs."""
        node = self.kwargs["node"]
        query = Q(requestee=node) | Q(requester=node)
        return ClaimRequest.objects.filter(query)


class ClaimRequestFieldView(
    generics.RetrieveUpdateAPIView, MultiPermissionView
):
    """API to retrieve claim requests details."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "PATCH": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
    }

    serializer_class = claimreq_serializers.ClaimRequestFieldSerializer

    def get_queryset(self):
        """Filter qs."""
        node = self.kwargs["node"]
        query = Q(claim_request__requestee=node) | Q(
            claim_request__requester=node
        )
        return ClaimRequestField.objects.filter(query)


class AttachRequestedClaim(APIView):
    """API to attach a claim after the requestee has added the files/fields."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    def post(self, request, *args, **kwargs):
        """Create overridden."""
        node = kwargs["node"]
        claim_request = ClaimRequest.objects.get(id=kwargs["pk"])
        if not claim_request.requester == node:
            raise BadRequest("Only requester can add the claim")
        claim_request_serializer = claimreq_serializers.ClaimRequestSerializer(
            claim_request, context={"view": self, "request": request}
        )
        (claim_request_serializer.attach_claim_from_request(claim_request))
        return comm_lib._success_response({}, "Claims attached", 200)
