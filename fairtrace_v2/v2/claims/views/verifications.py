"""Views for node related urls."""
from common import library as comm_lib
from common.drf_custom.views import MultiPermissionView
from common.exceptions import AccessForbidden
from common.exceptions import BadRequest
from common.exceptions import ParameterMissing
from rest_framework import generics
from v2.accounts import permissions as user_permissions
from v2.claims import constants
from v2.claims.filters import VerificationFilter
from v2.claims.models import AttachedClaim
from v2.claims.models import Claim
from v2.claims.serializers.verification import CommentSerializer
from v2.claims.serializers.verification import VerificationListSerializer
from v2.claims.serializers.verification import VerificationSerializer
from v2.communications import constants as notif_constants
from v2.communications.models import Notification
from v2.supply_chains import constants as sc_constants
from v2.supply_chains import filters as sc_filters
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.models import Node
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.serializers.node import NodeListSerializer
from v2.transactions import constants as trans_constants


class ListClaimVerifiers(generics.ListAPIView):
    """API to list the verifiers of a claims in a supply chain.

    Is a claim has a fixed verifier, only those companies can be
    assigned to verify Otherwise, Any company that you have invited, or
    the verifiers that Fairfood has assigned in a supply chains or your
    direct buyers can be assigned as verifiers
    """

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    filterset_class = sc_filters.NodeFilter
    serializer_class = NodeListSerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        claim_assignors = self.request.query_params.get("assigned_by", False)
        claim_verifiers = self.request.query_params.get("assigned_to", False)
        if claim_assignors == "true":
            return self._claim_assignors()
        if claim_verifiers == "true":
            return self._claim_verifiers()
        return self._all_verifiers()

    def _claim_verifiers(self):
        """To perform function _claim_verifiers."""
        node = self.kwargs["node"]
        _status = trans_constants.TRANSACTION_STATUS_DECLINED
        _ids = node.claims_attached.exclude(
            attachedbatchclaim__batch__source_transaction__status=_status
        ).values_list("verifier_id", flat=True)
        return Node.objects.filter(id__in=_ids)

    def _claim_assignors(self):
        """To perform function _claim_assignors."""
        node = self.kwargs["node"]
        _status = trans_constants.TRANSACTION_STATUS_DECLINED
        _ids = node.claim_verifications.exclude(
            attachedbatchclaim__batch__source_transaction__status=_status
        ).values_list("attached_by_id", flat=True)
        return Node.objects.filter(id__in=_ids)

    def _all_verifiers(self):
        """To perform function _all_verifiers."""
        node = self.kwargs["node"]
        try:
            sc_id = self.request.query_params["supply_chain"]
        except KeyError:
            raise ParameterMissing("supply_chain")
        claim_id = self.request.query_params.get("claim")
        if claim_id:
            claim = Claim.objects.get(id=comm_lib._decode(claim_id))
            claim_verifiers = claim.verifiers.all()
            if claim_verifiers:
                return claim_verifiers
        supply_chain = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
        verifiers = Node.objects.filter(
            # All nodes that you've invited in this supply chain
            invitations_received__inviter=node,
            invitations_received__connection__supply_chain=supply_chain,
        )
        verifiers |= (
            supply_chain.verifiers.all()
        )  # All verifiers in the supply chain
        verifiers |= node.get_buyers(supply_chain)  # All your direct buyers
        verifiers = (
            verifiers.distinct("id")
            .filter(type=sc_constants.NODE_TYPE_COMPANY)
            .distinct("id")
        )  # Filter only companies
        return verifiers


class ReceivedVerificationListView(generics.ListAPIView):
    """API to list the claim verifications received as a verifier."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = VerificationListSerializer

    filterset_class = VerificationFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        _status = trans_constants.TRANSACTION_STATUS_DECLINED
        return node.claim_verifications.all().exclude(
            attachedbatchclaim__batch__source_transaction__status=_status
        )


class SentVerificationListView(generics.ListAPIView):
    """API to list the verifications you've sent for verification."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = VerificationListSerializer

    filterset_class = VerificationFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        _status = trans_constants.TRANSACTION_STATUS_DECLINED
        return node.claims_attached.all().exclude(
            attachedbatchclaim__batch__source_transaction__status=_status
        )


class VerificationDetailsAPI(
    generics.RetrieveUpdateAPIView, MultiPermissionView
):
    """Get details and update verification."""

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

    serializer_class = VerificationSerializer

    queryset = AttachedClaim.objects.all()


class AttachedClaimAPI(
    generics.RetrieveUpdateDestroyAPIView, MultiPermissionView
):
    """Get details and update verification."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "PATCH": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
        "DELETE": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
    }

    serializer_class = VerificationSerializer

    queryset = AttachedClaim.objects.all()

    def delete(self, request, *args, **kwargs):
        """To perform function lete."""
        node = self.kwargs["node"]
        attached_claim = self.get_object()
        # remove all notifications related to this attached_claim.
        notifications = Notification.objects.filter(
            event_id=comm_lib._encode(attached_claim.id),
            type=notif_constants.NOTIF_TYPE_RECEIVE_VERIFICATION_REQUEST,
        )
        notifications.delete()
        if not attached_claim.claim.type == constants.CLAIM_TYPE_COMPANY:
            raise BadRequest("Only Company claims can be removed")
        if node not in [
            attached_claim.attached_by,
            attached_claim.attachedcompanyclaim.node,
        ]:
            raise AccessForbidden("Cannot remove the claim")
        super(AttachedClaimAPI, self).delete(request, *args, **kwargs)
        return comm_lib._success_response({}, "Delete successful", 200)


class CommentView(generics.CreateAPIView):
    """Class to handle CommentView and functions."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = CommentSerializer
