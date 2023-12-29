"""Views related to claims in claims app."""
from common import library as comm_lib
from common.drf_custom.paginators import LargePaginator
from common.drf_custom.views import MultiPermissionView
from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from v2.accounts import permissions as user_permissions
from v2.claims.constants import CLAIM_SCOPE_GLOBAL
from v2.claims.constants import CLAIM_SCOPE_LOCAL
from v2.claims.constants import FIELD_TYPE_OPTION
from v2.claims.constants import STATUS_APPROVED
from v2.claims.filters import ClaimFilter
from v2.claims.models import Claim
from v2.claims.models import Criterion
from v2.claims.models import CriterionField
from v2.claims.serializers import claims as claims_serializers
from v2.claims.serializers import company_claims
from v2.claims.serializers import configure as configure_claims_serializers
from v2.claims.serializers import product_claims
from v2.claims.serializers import transaction_claims
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.filters import NodeFilter
from v2.supply_chains.models import Node
from v2.supply_chains.models import SupplyChain


class ClaimsView(generics.ListCreateAPIView, MultiPermissionView):
    """API to list and create claims."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "POST": (
            user_permissions.IsAuthenticated,
            sc_permissions.IsFairfoodAdmin,
        ),
    }

    pagination_class = LargePaginator

    def get_serializer_class(self):
        """Fetch corresponding serializer class."""
        if self.request.method == "POST":
            return configure_claims_serializers.CreateClaimSerializer
        return claims_serializers.ClaimSerializer

    filterset_class = ClaimFilter

    def get_queryset(self):
        """Filter queryset."""
        exclude = self.request.query_params.get("exclude", None)
        node = self.kwargs["node"]
        query = Q(scope=CLAIM_SCOPE_GLOBAL)
        query |= Q(scope=CLAIM_SCOPE_LOCAL, owners=node)
        query &= Q(active=True)
        sc_id = self.request.query_params.get("supply_chain", None)
        if sc_id and sc_id != "null":
            supply_chain = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
            query &= Q(supply_chains=supply_chain)
        claim_ids = [
            i.id
            for i in Claim.objects.filter(query).order_by("id").distinct("id")
        ]
        claims = Claim.objects.filter(id__in=claim_ids).order_by("scope")
        if exclude:
            # here exclude the claims that already attached to the
            # supplier node.
            query_node = self.request.query_params.get("node", None)
            query_node = Node.objects.get(id=comm_lib._decode(query_node))
            queryset = query_node.claims.filter(
                claim__scope=CLAIM_SCOPE_GLOBAL
            )
            if node != query_node:
                queryset |= query_node.claims.filter(
                    claim__scope=CLAIM_SCOPE_LOCAL,
                    attached_by=node,
                    status=STATUS_APPROVED,
                )
                claim_list = queryset.values_list("claim__id", flat=True)
                claims = claims.exclude(id__in=claim_list)
        return claims


class AttachTransactionClaim(generics.CreateAPIView):
    """View to attach a claims to transactions."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = transaction_claims.AttachClaimSerializer


class AttachBatchClaim(generics.CreateAPIView):
    """View to attach a claims to transactions."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = product_claims.AttachBatchClaimSerializer


class AttachCompanyClaim(generics.CreateAPIView):
    """View to attach a claims to transactions."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = company_claims.AttachCompanyClaimSerializer


class TransactionClaimData(generics.CreateAPIView):
    """View to attach a claims to transactions."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = (
        transaction_claims.TransactionCriterionFieldResponseSerializer
    )


class BatchClaimData(generics.CreateAPIView):
    """View to attach a claims to transactions."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = product_claims.BatchCriterionFieldResponseSerializer


class NodeClaimData(generics.CreateAPIView):
    """View to attach a claims to transactions."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = company_claims.NodeCriterionFieldResponseSerializer


class GetInheritableClaims(generics.CreateAPIView):
    """View to verify which claims can be inherited in a list of batches."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = claims_serializers.InheritableClaimsSerializer


class ListAttachedNodeClaims(generics.ListAPIView):
    """View to verify which claims can be inherited in a list of batches."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = company_claims.CompanyClaimSerializer

    def get_queryset(self):
        """Filter queryset."""
        node = self.kwargs["node"]
        pk = self.kwargs["pk"]
        query_node = Node.objects.get(id=pk)
        queryset = query_node.claims.filter(claim__scope=CLAIM_SCOPE_GLOBAL)
        if node != query_node:
            queryset |= query_node.claims.filter(
                claim__scope=CLAIM_SCOPE_LOCAL, attached_by=node
            )
        return queryset


class ClaimsRetrieveDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Update and delete API for claims."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = configure_claims_serializers.CreateClaimSerializer
    queryset = Claim.objects.all()


class CriterionList(generics.ListCreateAPIView):
    """API to List and create a criterion for claim."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = configure_claims_serializers.CreateCriterionSerializer

    def create(self, request, *args, **kwargs):
        """Overridden create."""
        data = (
            request.data.get("criteria")
            if "criteria" in request.data
            else request.data
        )
        many = isinstance(data, list)
        serializer = self.get_serializer(data=data, many=many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, headers=headers)


class CriteriaRetrieveDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Update and delete API for criterion."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = configure_claims_serializers.CreateCriterionSerializer
    queryset = Criterion.objects.all()


class CriterionFieldList(generics.CreateAPIView):
    """API to List and create a criterion field for criteria."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = (
        configure_claims_serializers.CreateCriterionFieldSerializer
    )

    def create(self, request, *args, **kwargs):
        """Overridden create()."""
        data = (
            request.data.get("criterion_field")
            if "criterion_field" in request.data
            else request.data
        )
        for i in range(len(data)):
            if data[i]["type"] == FIELD_TYPE_OPTION:
                options = ",".join(data[i]["options"])
                data[i]["options"] = options
            else:
                data[i]["options"] = "null"
        many = isinstance(data, list)
        serializer = self.get_serializer(data=data, many=many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, headers=headers)


class CriterionFieldRetrieveDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Update and delete API for criterion field."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = (
        configure_claims_serializers.CreateCriterionFieldSerializer
    )
    queryset = CriterionField.objects.all()


class FFAdminClaimsView(generics.ListAPIView):
    """API to list claims."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = configure_claims_serializers.CreateClaimSerializer

    filterset_class = ClaimFilter

    queryset = Claim.objects.filter(latest=True).order_by(
        "-active", "-created_on"
    )


class FFAdminVerifierView(generics.ListAPIView):
    """API to list verifiers."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = claims_serializers.FFAdminVerifierSerializer

    filterset_class = NodeFilter

    def get_queryset(self):
        """Filter qs."""
        return Node.objects.all().exclude(verifier_sc_objects=None)


class FFAdminClaimDetails(generics.RetrieveAPIView):
    """Claim details API."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = claims_serializers.ClaimSerializer

    filterset_class = ClaimFilter

    def get_queryset(self):
        """Filter qs."""
        query = Q(scope=CLAIM_SCOPE_GLOBAL)
        query |= Q(scope=CLAIM_SCOPE_LOCAL)
        sc_id = self.request.query_params.get("supply_chain", None)
        if sc_id:
            supply_chain = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
            query &= Q(supply_chains=supply_chain)
        claim_ids = [
            i.id
            for i in Claim.objects.filter(query).order_by("id").distinct("id")
        ]
        return Claim.objects.filter(id__in=claim_ids).order_by("scope")
