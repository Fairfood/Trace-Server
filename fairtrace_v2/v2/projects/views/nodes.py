"""View for node related APIs in the project."""
from common.drf_custom.views import MultiPermissionView
from common.exceptions import BadRequest
from rest_framework import generics
from . import check_node
from v2.accounts import permissions as user_permissions
from v2.projects import filters
from v2.projects import permissions as project_permissions
from v2.projects.models import NodeCard
from v2.projects.models import Project
from v2.projects.serializers import nodes as project_node_ser
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer


class ProjectSupplierListAPI(generics.ListAPIView):
    """API to list the products in a project."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )
    filterset_class = filters.FilterNodes

    serializer_class = project_node_ser.ProjectFarmerReadOnlySerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        pk = self.kwargs["pk"]
        try:
            project = Project.objects.get(id=pk)
        except Exception:
            raise BadRequest("Invalid project id")

        suppliers = node.get_suppliers(supply_chain=project.supply_chain)
        proj_suppliers = project.member_nodes.filter(id__in=suppliers)
        return Farmer.objects.filter(node_ptr__in=proj_suppliers)


class ProjectBuyerListAPI(generics.ListAPIView):
    """API to list the products in a project."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )
    filterset_class = filters.FilterNodes

    serializer_class = project_node_ser.ProjectCompanySerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        pk = self.kwargs["pk"]
        project = Project.objects.get(id=pk)
        buyers = node.get_buyers(supply_chain=project.supply_chain)
        proj_buyers = project.member_nodes.filter(id__in=buyers)
        return Company.objects.filter(node_ptr__in=proj_buyers)


class FarmerInviteAPI(generics.CreateAPIView):
    """API to invite farmers to the project."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
        project_permissions.HasProjectAccess,
    )

    serializer_class = project_node_ser.ProjectFarmerInviteSerializer


class FarmerDetails(generics.RetrieveUpdateAPIView, MultiPermissionView):
    """This class will retrieve and updates farmer details."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticated,
            sc_permissions.HasNodeAccess,
        ),
        "PATCH": (
            user_permissions.IsAuthenticated,
            sc_permissions.HasNodeWriteAccess,
            sc_permissions.HasIndirectNodeAccess,
        ),
    }

    serializer_class = project_node_ser.ProjectFarmerSerializer

    queryset = Farmer.objects.all()


class FarmerDetailsAPI(generics.ListAPIView):
    """API to get app Farmer details."""

    permission_classes = (user_permissions.OpenValidTOTP,)
    serializer_class = project_node_ser.AppFarmerSerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        try:
            fair_id = (
                str(self.kwargs["pk"]).upper().lstrip("FF").replace(" ", "")
            )
            node = NodeCard.objects.get(
                fairid__iexact=fair_id, node__type=NODE_TYPE_FARM
            ).node
        except Exception:
            raise BadRequest("Invalid card number")
        check_node(self.request, node)
        return  Farmer.objects.filter(id=node.id)


