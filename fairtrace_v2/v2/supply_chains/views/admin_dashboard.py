"""Views for admin dashboard related urls."""
from common import library as comm_lib
from common import library as common_lib
from common.exceptions import BadRequest
from django.db.models import Count
from django.db.models import Q
from rest_framework import generics
from rest_framework.views import APIView
from v2.accounts import permissions as user_permissions
from v2.activity.models import Activity
from v2.activity.serializers.activity import NodeActivitySerializer
from v2.products.constants import PRODUCT_TYPE_GLOBAL
from v2.products.constants import PRODUCT_TYPE_LOCAL
from v2.products.filters import ProductFilter
from v2.products.models import Product
from v2.supply_chains import constants
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.filters import CompanyFilter
from v2.supply_chains.filters import SupplyChainFilter
from v2.supply_chains.models import Company
from v2.supply_chains.models import NodeMember
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.models import Verifier
from v2.supply_chains.serializers import admin_dashboard as admin_serializers
from v2.supply_chains.serializers.public import SupplyChainSerializer


class FFAdminSupplyChainList(generics.ListAPIView):
    """Class to handle FFAdminSupplyChainList and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )
    serializer_class = SupplyChainSerializer
    queryset = SupplyChain.objects.all().order_by("name")


class FFAdminInviteCompany(generics.CreateAPIView):
    """Class to handle FFAdminInviteCompany and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminCompanyInviteSerializer


class FFAdminCompanyView(generics.ListAPIView):
    """Class to handle FFAdminCompanyView and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    # search_fields = ['name']
    # filter_backends = (filters.SearchFilter,)
    filterset_class = CompanyFilter
    queryset = Company.objects.filter(plan=constants.NODE_PLAN_PREMIUM)
    serializer_class = admin_serializers.FFAdminCompanyListSerializer


class FFAdminCompanyDetails(generics.RetrieveUpdateAPIView):
    """This class will retrieve and update company."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    queryset = Company.objects.all()
    serializer_class = admin_serializers.FFAdminCompanySerializer


class FFAdminNodeMemberView(generics.ListCreateAPIView):
    """API to get company member list."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminNodeMemberSerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        return NodeMember.objects.filter(node=self.kwargs["pk"]).order_by(
            "type",
            "created_on",
        )


class FFAdminNodeMemberDetailsView(generics.RetrieveUpdateDestroyAPIView):
    """API to retrieve company member details."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminNodeMemberSerializer
    queryset = NodeMember.objects.all()

    def delete(self, request, *args, **kwargs):
        """To perform function lete."""
        member = self.get_object()
        member.delete(user=request.user)
        return comm_lib._success_response({}, "Delete successful", 200)


class FFAdminResendNodeMemberInvite(APIView):
    """Class to handle FFAdminResendNodeMemberInvite and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    @staticmethod
    def post(request, user, pk, *args, **kwargs):
        """
        Resend invite to node member
        Args:
            request:
            user:
            node:
        Returns:
        """
        try:
            nodemember = NodeMember.objects.get(id=pk)
        except Exception:
            raise BadRequest("Invalid node member id")
        nodemember.send_invite(sender=user)
        return comm_lib._success_response({}, "Resend successful", 200)


class FFAdminCompanyActivity(generics.ListAPIView):
    """API to get company activity list."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = NodeActivitySerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["pk"]
        return Activity.objects.filter(node=node)


class FFAdminSupplyChainView(generics.ListCreateAPIView):
    """API to listing node supplychain list."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminSupplyChainViewSerializer
    filterset_class = SupplyChainFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        _type = constants.NODE_TYPE_COMPANY
        supplychain = (
            SupplyChain.objects.all()
            .annotate(
                active_actor_count=(
                    Count(
                        "nodesupplychain",
                        filter=Q(nodesupplychain__node__type=_type),
                    )
                    - Count(
                        "nodesupplychain",
                        filter=Q(
                            nodesupplychain__node__type=_type,
                            nodesupplychain__node__date_joined=None,
                        ),
                    )
                ),
                farmer_count=Count(
                    "nodesupplychain",
                    filter=Q(
                        nodesupplychain__node__type=constants.NODE_TYPE_FARM
                    ),
                ),
            )
            .order_by("-active_actor_count")
        )

        return supplychain


class SupplyChainListView(generics.ListAPIView):
    """API to retrieve company member details."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminSupplyChainSerializer
    queryset = SupplyChain.objects.all()


class UpdateSupplyChain(generics.RetrieveUpdateAPIView):
    """API to retrieve supply chain details."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = SupplyChainSerializer
    queryset = SupplyChain.objects.all()


class FFAdminProductView(generics.ListCreateAPIView):
    """API to list and create Products based on a supplychain."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminProductSerializer
    filterset_class = ProductFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        query = Q(type=PRODUCT_TYPE_GLOBAL)
        query |= Q(type=PRODUCT_TYPE_LOCAL)
        return Product.objects.filter(query)


class FFAdminUpdateProduct(generics.RetrieveUpdateAPIView):
    """API to retrieve supply chain details."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminProductSerializer
    queryset = Product.objects.all()


class FFAdminResendInvite(generics.CreateAPIView):
    """Class to handle FFAdminResendInvite and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminResendInviteSerializer


class FFAdminNodeThemeView(generics.CreateAPIView):
    """Class to handle FFAdminNodeThemeView and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminNodeThemeViewSerializer


class FFAdminNodeVerifier(generics.CreateAPIView, generics.DestroyAPIView):
    """Class to handle FFAdminNodeVerifier and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = admin_serializers.FFAdminNodeVerifierSerializer
    queryset = Verifier.objects.all()

    def delete(self, request, *args, **kwargs):
        """To perform function lete."""
        supply_chain = common_lib._decode(request.data["supply_chain"])
        verifier = Verifier.objects.filter(
            node=self.kwargs["pk"], supply_chain=supply_chain
        )
        if not verifier:
            raise BadRequest("Supply_chain already deleted")
        verifier.delete()
        return comm_lib._success_response({}, "Delete successful", 200)
