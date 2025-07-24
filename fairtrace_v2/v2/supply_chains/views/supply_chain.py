"""Views for node related urls."""
from common import library as comm_lib
from common.drf_custom.paginators import LargePaginator
from common.drf_custom.views import MultiPermissionView
from common.exceptions import BadRequest
from common.library import decode
from django.db import transaction
from django.db.models import F
from django.db.models import Q
from django.http import HttpResponse
from django.utils import translation
from rest_framework import generics
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from v2.accounts import permissions as user_permissions
from v2.dashboard.models import NodeStats
from v2.products.constants import PRODUCT_TYPE_GLOBAL
from v2.products.constants import PRODUCT_TYPE_LOCAL
from v2.products.filters import ProductFilter
from v2.products.models import Product
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.constants import (
    INVITE_RELATION_BUYER, INVITE_RELATION_SUPPLIER, NODE_TYPE_FARM
)
from v2.supply_chains.farmer_bulk import export_farmers
from v2.supply_chains.farmer_bulk.constants import farmer_excel_file_name
from v2.supply_chains.filters import LabelFilter
from v2.supply_chains.filters import NodeFilter, ConnectionNodeFilter
from v2.supply_chains.filters import SupplyChainFilter
from v2.supply_chains.models import (
    Connection, Label, Node, NodeSupplyChain, SupplyChain, Invitation
)
from v2.supply_chains.serializers import supply_chain as sc_serializers
from v2.supply_chains.serializers.supply_chain import ConnectionNodeSerializer

""" Views for node related urls"""


class SupplyChainList(generics.ListAPIView):
    """API to get suppl-chain list."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )
    serializer_class = sc_serializers.SupplyChainSerializer
    pagination_class = LargePaginator
    filterset_class = SupplyChainFilter

    def get_queryset(self):
        """Returns the filtered qs."""
        node = self.kwargs["node"]
        return (
            node.supply_chains.filter(active=True)
            .order_by("name")
            .distinct("name")
        )


class InviteCompany(generics.CreateAPIView):
    """API to invite company."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = sc_serializers.CompanyInviteSerializer


class InviteFarmer(generics.CreateAPIView):
    """API to invite farmer."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = sc_serializers.FarmerInviteSerializer


class MapConnectionView(generics.RetrieveAPIView):
    """API to map connection view."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )
    cache_prefix = "connection"

    serializer_class = sc_serializers.MapConnectionsSerializer

    queryset = Node.objects.all()

    def retrieve(self, request, *args, **kwargs):
        """To perform function retrieve."""
        instance = self.get_object()
        supply_chain = request.query_params.get("supply_chain")
        data = self._cache_response(instance, supply_chain)
        return Response(data)

    def _cache_response(self, instance, *args):
        """To perform function _cache_response."""
        # if not self.cache_prefix:
        #     self.cache_prefix = self.__class__.__name__
        # key = '_'.join([self.cache_prefix, str(instance.id),
        #                 *[str(decode(obj)) for obj in args]])
        # key = self._clean_key(key)
        # data = filesystem_cache.get(key)
        # if data:
        #     return data
        serializer = self.serializer_class(
            instance, context={"request": self.request}
        )
        data = serializer.data
        # filesystem_cache.set(key, data)
        return data

    @staticmethod
    def _clean_key(key):
        """To perform function _clean_key."""
        current_language = translation.get_language()
        key = key + "_" + current_language
        return key


class TableConnectionView(generics.RetrieveAPIView):
    """API to table connection view."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = sc_serializers.TableConnectionsSerializer

    queryset = Node.objects.all()


class FarmerTemplate(MultiPermissionView):
    """API to get export farmer template and bulk update."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "POST": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
        ),
    }

    # permissions = {
    #     'GET': (),
    #     'POST': (
    #         user_permissions.IsAuthenticatedWithVerifiedEmail,)
    # }

    @staticmethod
    def get(request, user, node, *args, **kwargs):
        """Returns the template file."""
        extra_fields = request.query_params.get("fields", "")
        extra_fields = extra_fields.split(",") if extra_fields else []
        supply_chain_id = request.query_params.get("supply_chain", None)
        connection_id = request.query_params.get("connection", None)
        if not supply_chain_id:
            raise BadRequest("Supply chain ID is required as query parameter")
        supply_chain = SupplyChain.objects.get(
            id=comm_lib._decode(supply_chain_id)
        )
        if connection_id:
            connection = Node.objects.get(id=comm_lib._decode(connection_id))
        else:
            connection = node

        file = export_farmers(
            connection, supply_chain=supply_chain, visible_fields=extra_fields
        )

        response = HttpResponse(
            file,
            content_type="application/vnd.openxmlformats"
            + "-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            "attachment; filename=%s" % farmer_excel_file_name
        )

        return response

    def post(self, request, user, *args, **kwargs):
        """Save the farmer template."""
        serializer = sc_serializers.FarmerTemplateSerializer(
            data=request.data, context={"request": request, "view": self}
        )
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)
        serializer.save()

        return comm_lib._success_response(serializer.data)


class FarmerBulkInviteUpdate(generics.CreateAPIView):
    """API to bulk invite update."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = sc_serializers.FarmerBulkSerializer


class ResendInvite(generics.CreateAPIView):
    """API to resent invite."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = sc_serializers.ResendInviteSerializer


class UpdateTag(generics.UpdateAPIView):
    """API to update tag."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = sc_serializers.UpdateTagSerializer

    queryset = Node.objects.all()


class SearchNode(APIView):
    """APIs to search nodes."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    def get(self, request, user, node, pk, *args, **kwargs):
        """Returns list of nodes."""
        sc_id = request.query_params.get("supply_chain", None)
        supply_chain = (
            SupplyChain.objects.get(id=comm_lib._decode(sc_id))
            if sc_id
            else None
        )
        target_node = Node.objects.get(id=pk)
        data = sc_serializers.NodeSearch(node, supply_chain).search_node(
            target_node
        )
        return comm_lib._success_response(data)


class GetBuyers(generics.ListAPIView):
    """API to get T1 buyers of a node filterable by supply chain."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    filterset_class = NodeFilter

    serializer_class = sc_serializers.NodeBasicSerializer

    def get_queryset(self, *args, **kwargs):
        """Filter queryset."""
        node = self.kwargs["node"]
        sc_id = comm_lib._decode(
            self.request.query_params.get("supply_chain", None)
        )
        supply_chain = None
        if sc_id:
            supply_chain = SupplyChain.objects.get(id=sc_id)
        return (
            node.get_buyers(supply_chain=supply_chain)
            .distinct("date_joined", "id")
            .order_by(F("date_joined").desc(nulls_last=True))
        )


class GetSuppliers(generics.ListAPIView):
    """API to get T1 suppliers of a node filterable by supply chain."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    filterset_class = NodeFilter

    serializer_class = sc_serializers.NodeBasicSerializer

    def get_queryset(self, *args, **kwargs):
        """Filter queryset."""
        node = self.kwargs["node"]
        sc_id = comm_lib._decode(
            self.request.query_params.get("supply_chain", None)
        )
        supply_chain = None
        if sc_id:
            supply_chain = SupplyChain.objects.get(id=sc_id)
        # return node.get_suppliers(supply_chain=supply_chain).distinct('id')
        return (
            node.get_suppliers(supply_chain=supply_chain)
            .distinct("date_joined", "id")
            .order_by(F("date_joined").desc(nulls_last=True))
        )


class AddNodeSupplyChains(generics.CreateAPIView):
    """API to create supply chain in company or listing node supplychain
    details."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    serializer_class = sc_serializers.AddNodeSupplyChainSerializer

    # filterset_class = NodeSupplyChainFilter

    def get_queryset(self):
        """Filter queryset."""
        node_supply_chain = NodeSupplyChain.objects.filter(
            node=self.kwargs["pk"]
        ).order_by("active_actor_count")
        return node_supply_chain


class RemoveNodeSupplyChain(generics.DestroyAPIView):
    """API to delete company supply chain."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.IsFairfoodAdmin,
    )

    queryset = NodeSupplyChain.objects.all()


class SupplyChainActive(APIView):
    """API to make active supplychain."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    @staticmethod
    def post(request, user, node, pk, *args, **kwargs):
        """Overridden post make supply chain active."""
        try:
            node_supply_chain = NodeSupplyChain.objects.get(
                supply_chain__id=pk, node=node
            )
        except Exception:
            raise BadRequest("Invalid")
        node_supply_chain.make_active()
        return comm_lib._success_response({}, "successful", 200)


class NodeSupplyChains(generics.ListAPIView):
    """API to create supply chain in company or listing node supplychain
    details."""

    permission_classes = (user_permissions.IsAuthenticated,)

    serializer_class = sc_serializers.NodeSupplyChainSerializer

    def get_queryset(self):
        """Filter queryset."""
        node_supply_chain = NodeSupplyChain.objects.filter(
            node=self.kwargs["pk"]
        ).order_by("-actor_count")
        node_stats = NodeStats.objects.get(node=self.kwargs["pk"])
        if node_stats.is_outdated:
            node_stats.update_values()
        return node_supply_chain


class UpdateConnectionLabel(generics.UpdateAPIView):
    """Api to update connection label."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = sc_serializers.ConnecionLabelSerializer

    queryset = Connection.objects.all()


class LabelsAPI(generics.ListCreateAPIView):
    """Api to list labels."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    filterset_class = LabelFilter
    serializer_class = sc_serializers.LabelSerializer

    queryset = Label.objects.all()

    def get_queryset(self):
        """Filter queryset."""
        return (
            Label.objects.filter(added_by=self.kwargs["node"])
            .distinct("id")
            .order_by("-id")
        )


class RetrieveUpdateDestroyLabels(generics.RetrieveUpdateDestroyAPIView):
    """APIs to update, retrieve and delete Labels."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = sc_serializers.LabelSerializer

    queryset = Label.objects.all()

    def delete(self, request, *args, **kwargs):
        """Validate before delete()"""
        node = self.kwargs["node"]
        label = self.get_object()
        if label.added_by != node:
            raise BadRequest(
                f"Node {node.full_name} cannot delete label {label.name}"
            )
        super(RetrieveUpdateDestroyLabels, self).delete(
            request, *args, **kwargs
        )
        return comm_lib._success_response({}, "Delete successful", 200)


class ProductView(generics.ListCreateAPIView):
    """API to list and create Products based on a supplychain."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = sc_serializers.ProductSerializer
    filterset_class = ProductFilter

    def get_queryset(self):
        """Filter queryset."""
        query = Q(type=PRODUCT_TYPE_GLOBAL)
        query |= Q(type=PRODUCT_TYPE_LOCAL)
        return Product.objects.filter(query)


class ConnectionNodeViewSet(viewsets.ModelViewSet):
    """Viewset for managing ConnectionNode instances.

    This viewset allows performing GET operation on the ConnectionNode model.


    Attributes:
        permission_classes (tuple): A tuple of permission classes for the
                                    viewset.
        serializer_class: The serializer class used for serializing and
                          deserializing the ConnectionNode model.
    """

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )
    serializer_class = ConnectionNodeSerializer
    allowed_methods = ("GET",)
    filterset_class = ConnectionNodeFilter

    def get_queryset(self):
        """Get the queryset of Node objects for the ConnectionNodeViewSet.

        This method retrieves the queryset of Node objects based on the
        provided criteria, such as the 'node' parameter from the URL kwargs,
        the supply chain obtained through the get_supply_chain() method, the
        'relationship' query parameter from the request, and any additional
        query parameters from the request.

        Returns:
            QuerySet: The queryset of Node objects.
        """
        node = self.kwargs.get("node")
        supply_chain = self.get_supply_chain()

        connection_type = self.request.query_params.get("relationship")
        connection_type = int(connection_type) if connection_type else None

        suppliers, buyers = [], []
        if connection_type != INVITE_RELATION_BUYER:
            suppliers = node.map_supplier_pks(supply_chain=supply_chain)
        if connection_type != INVITE_RELATION_SUPPLIER:
            buyers = node.map_buyer_pks(supply_chain=supply_chain)

        return Node.objects.filter(
            Q(pk__in=suppliers) | Q(pk__in=buyers)
        ).filter_queryset(self.request).distinct()

    def get_supply_chain(self):
        """Get and validate the supply chain.

        This method retrieves and validates the supply chain based on the
        'supply_chain' query parameter in the request.
        It decodes the encoded supply chain ID, performs a database query to
        fetch the corresponding supply chain, and returns it.

        Returns:
            SupplyChain: The retrieved and validated supply chain.

        Raises:
            ValidationError: If the 'supply_chain' query parameter is not
            provided or the supply chain is not found.
        """
        # get and validate supply-chain
        supply_chain_idencode = self.request.query_params.get("supply_chain")
        try:
            return SupplyChain.objects.get(pk=decode(supply_chain_idencode))
        except SupplyChain.DoesNotExist:
            raise ValidationError(
                detail="?supply_chain is not provided " "or not valid"
            )


class CarbonConnectionView(generics.GenericAPIView):
    """
    View to create connections of existing farmers of a company to a target 
    company for carbon transactions
    """

    def post(self, request, *args, **kwargs):
        """Override post to create connection and invitation"""
        data = request.data
        supply_chain = SupplyChain.objects.get(id=decode(data["supply_chain"]))
        source_company = Node.objects.get(id=decode(data["source_company"]))
        target_company = Node.objects.get(id=decode(data["target_company"]))
        farmers = source_company.get_suppliers().filter(type=NODE_TYPE_FARM)

        with transaction.atomic():
            for farmer in farmers:
                invitation, _ = Invitation.objects.get_or_create(
                    inviter=target_company,
                    message="Added through carbon connections",
                    invitee=farmer,
                )
                connection, _ = Connection.objects.get_or_create(
                    buyer=target_company, 
                    supplier=farmer, 
                    supply_chain=supply_chain
                )
                invitation.connection = connection
                invitation.save()
        target_company.verify_connections()
        data = ConnectionNodeSerializer(
            target_company.get_suppliers(), many=True
        ).data
        return Response(data)