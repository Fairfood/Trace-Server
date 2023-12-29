"""Views for node related urls."""
from common import library as comm_lib
from common.drf_custom.paginators import LargePaginator
from common.drf_custom.views import MultiPermissionView
from common.exceptions import AccessForbidden
from common.exceptions import BadRequest
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.functions import Lower
from rest_framework import filters
from rest_framework import generics
from rest_framework.views import APIView
from v2.accounts import permissions as user_permissions
from v2.supply_chains import filters as sc_filters
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import NodeDocument
from v2.supply_chains.models import NodeMember
from v2.supply_chains.models import Operation
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.serializers.node import CompanyListSerializer
from v2.supply_chains.serializers.node import CompanySerializer
from v2.supply_chains.serializers.node import FarmerListSerializer
from v2.supply_chains.serializers.node import FarmerSerializer
from v2.supply_chains.serializers.node import NodeDocumentSerializer
from v2.supply_chains.serializers.node import NodeMemberSerializer
from v2.supply_chains.serializers.node import NodeMemberUpdateSerializer
from v2.supply_chains.serializers.node import NodeWalletSerializer
from v2.supply_chains.serializers.node import OperationSerializer
from v2.supply_chains.serializers.node import ValidateCompanyNameSerializer
from v2.supply_chains.serializers.node import ValidateFarmerIDSerializer
from v2.supply_chains.serializers.public import NodeBasicSerializer

# from v2.supply_chains.models import Node


class ValidateCompanyName(APIView):
    """View to validate company name.

    Checks if company with same name exists
    """

    permission_classes = (user_permissions.IsAuthenticated,)

    serializer_class = ValidateCompanyNameSerializer

    @staticmethod
    def post(request, user, *args, **kwargs):
        """Function to get username availability.

        Request Params:
            username(str): user name.
            type(int): type of user account.
        Response:
            Response. with,
            success(bool): success status of the response.
            message(str): Status description message.
            code(int): status code.
            data(dict): data info.
                valid(bool): true or false value.
                available(bool): true or false value.
                message(str): validation message
        """
        serializer = ValidateCompanyNameSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)

        return comm_lib._success_response(serializer.data)


class FarmerView(generics.ListCreateAPIView, MultiPermissionView):
    """APIs for farmer views."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "POST": (user_permissions.IsAuthenticated,),
    }

    search_fields = ["first_name", "last_name"]
    filter_backends = (filters.SearchFilter,)

    def get_serializer_class(self):
        """Fetch corresponding serializer class."""
        if self.request.method == "POST":
            return FarmerSerializer
        return FarmerListSerializer

    def get_queryset(self):
        """Returns the filtered qs."""
        try:
            sc_id = self.request.query_params["supply_chain"]
            supply_chain = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
        except KeyError:
            raise BadRequest("supply_chain is required in url params.")
        except ObjectDoesNotExist:
            raise BadRequest("Invalid Supplychain id.")
        connected_nodes = self.kwargs["node"].get_suppliers(
            supply_chain=supply_chain
        )
        return Farmer.objects.filter(node_ptr__in=connected_nodes)


class ManagedFarmers(generics.ListAPIView):
    """API for listing managed farmers."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    filterset_class = sc_filters.FarmerFilter
    serializer_class = FarmerSerializer

    def get_queryset(self):
        """Returns the filtered qs."""
        node = self.kwargs["node"]
        return Farmer.objects.filter(managers=node)


class CompanyView(generics.ListCreateAPIView, MultiPermissionView):
    """APIs for company view."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "POST": (user_permissions.IsAuthenticated,),
    }
    search_fields = ["name"]
    filter_backends = (filters.SearchFilter,)

    def list(self, request, *args, **kwargs):
        """To reduce api load removing 'connected' and 'connectable' fields
        from the api with a flag passed through url
        '/?connection_status=false'."""
        connection_status = self.request.query_params.get(
            "connection_status", True
        )
        removed_fields = None
        if connection_status == "false":
            removed_fields = self._build_serializer()
        response = super(CompanyView, self).list(request, *args, **kwargs)
        if removed_fields:
            self._reset_serializer(removed_fields)
        return response

    def get_queryset(self):
        """Returns the filtered qs."""
        node = self.kwargs["node"]
        connected_key = self.request.query_params.get("connected", None)
        connected = True if connected_key == "true" else False
        sc_id = self.request.query_params.get("supply_chain", None)
        if sc_id:
            supply_chain = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
        else:
            supply_chain = None
        if connected:
            connected_nodes = node.get_buyers(supply_chain=supply_chain)
            # connected_nodes |= Node.objects.filter(id=node.id)
            return Company.objects.filter(node_ptr__in=connected_nodes)
        return (
            Company.objects.all()
            .exclude(node_ptr=self.kwargs["node"])
            .annotate(lower_name=Lower("name"))
            .distinct("lower_name", "id")
            .order_by("lower_name")
        )

    def get_serializer_class(self):
        """Fetch corresponding serializer class."""
        if self.request.method == "POST":
            return CompanySerializer
        return CompanyListSerializer

    def _build_serializer(self) -> dict:
        """Dynamically rebuild the serializer with removed fields and return
        the removed fields for resting in future."""
        fields = {}
        serializer_class = self.get_serializer_class()
        fields["connected"] = serializer_class._declared_fields.pop(
            "connected", None
        )
        fields["connectable"] = serializer_class._declared_fields.pop(
            "connectable", None
        )
        serializer_class.Meta.fields = ("id", "name", "image", "email_sent")
        return fields

    def _reset_serializer(self, removed_fields: dict) -> None:
        """Resting serializer with removed_fields to its original form.

        This is mandatory to avoid conflicts with changed signature of
        the serializer class.
        """
        serializer_class = self.get_serializer_class()
        declared_fields = list(serializer_class.Meta.fields)
        for key, value in removed_fields.items():
            serializer_class._declared_fields[key] = value
            declared_fields.append(key)
        serializer_class.Meta.fields = declared_fields


class MyConnections(generics.ListAPIView):
    """API for listing my connections."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = NodeBasicSerializer

    def get_queryset(self):
        """Returns the filtered qs."""
        node = self.kwargs["node"]
        sc_id = self.request.query_params.get("supply_chain", None)
        sc = None
        if sc_id:
            sc = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
        return node.get_connections(supply_chain=sc)


class CreateListNodeMember(generics.ListCreateAPIView, MultiPermissionView):
    """APIs for node member objects."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "POST": (
            (
                user_permissions.IsAuthenticatedWithVerifiedEmail
                & sc_permissions.HasNodeAdminAccess
            ),
        ),
    }

    serializer_class = NodeMemberSerializer

    def get_queryset(self):
        """Returns the filtered qs."""
        return NodeMember.objects.filter(node=self.kwargs["node"]).order_by(
            "type",
            "created_on",
        )


class OperationsList(generics.ListAPIView):
    """This class list all the operations."""

    permission_classes = (user_permissions.IsAuthenticated,)

    serializer_class = OperationSerializer
    pagination_class = LargePaginator

    def get_queryset(self):
        """Returns the filtered qs."""
        queryset = Operation.objects.all().order_by("name")

        node_type = self.request.query_params.get("node_type")
        if node_type:
            queryset = queryset.filter(node_type=node_type)

        try:
            sc_id = self.request.query_params["supply_chain"]
            supply_chain = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
            queryset = queryset.filter(supply_chains=supply_chain)
        except Exception:
            pass
            # TODO: make filter by supply chain ID mandatory.
            # raise BadRequest(
            #     "Invalid supply chain ID. "
            #     "Supplychain ID is mandatory for listing Operations"
            # )

        return queryset


class FarmerDetails(generics.RetrieveUpdateAPIView, MultiPermissionView):
    """This class will retrieve and updates farmer details."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "PATCH": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
            sc_permissions.HasIndirectNodeAccess,
        ),
    }

    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer


class CompanyDetails(generics.RetrieveUpdateAPIView, MultiPermissionView):
    """This class will retrieve and update company."""

    permissions = {
        "GET": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeAccess,
        ),
        "PATCH": (
            user_permissions.IsAuthenticatedWithVerifiedEmail,
            sc_permissions.HasNodeWriteAccess,
            sc_permissions.HasIndirectNodeAccess,
        ),
    }

    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class AddListNodeDocument(generics.ListCreateAPIView, MultiPermissionView):
    """API to create node documents."""

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

    serializer_class = NodeDocumentSerializer

    def get_queryset(self):
        """Returns filtered qs."""
        return NodeDocument.objects.filter(node=self.kwargs["node"])


class DeleteNodeDocument(generics.DestroyAPIView):
    """API to delete node documents."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    queryset = NodeDocument.objects.all()
    serializer_class = NodeDocumentSerializer

    def delete(self, request, *args, **kwargs):
        """delete an object."""
        document = self.get_object()
        if not document.node == kwargs["node"]:
            raise AccessForbidden()
        document.log_delete_activity(kwargs["user"])
        super(DeleteNodeDocument, self).delete(request, *args, **kwargs)
        return comm_lib._success_response({}, "Delete successful", 200)


class ResendNodeMemberInvite(APIView):
    """API to Resend invite."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    @staticmethod
    def post(request, user, node, pk, *args, **kwargs):
        """
        Resend invite to node member
        Args:
            request:
            user:
            node:
        Returns:
        """
        try:
            nodemember = NodeMember.objects.get(id=pk, node=node)
        except Exception:
            raise BadRequest("Invalid node member id")
        nodemember.send_invite(sender=user)
        return comm_lib._success_response({}, "Resend successful", 200)


class GetUpdateRemoveNodeMember(generics.RetrieveUpdateDestroyAPIView):
    """API to delete node member."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAdminAccess,
    )

    serializer_class = NodeMemberUpdateSerializer

    def get_queryset(self, *args, **kwargs):
        """Returns the filtered qs."""
        return NodeMember.objects.filter(node=self.kwargs["node"]).exclude(
            user=self.kwargs["user"]
        )

    def delete(self, request, *args, **kwargs):
        """Delete object."""
        member = self.get_object()
        member.delete(user=request.user)
        return comm_lib._success_response({}, "Delete successful", 200)


class ListNodeWallets(generics.ListAPIView):
    """API to list the wallets of a company."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = NodeWalletSerializer

    pagination_class = LargePaginator

    def get_queryset(self, *args, **kwargs):
        """returns qs."""
        return self.kwargs["node"].wallets.all()


class ValidateFarmerID(generics.RetrieveAPIView):
    """View to check farmer id exists."""

    serializer_class = ValidateFarmerIDSerializer

    @staticmethod
    def post(request, *args, **kwargs):
        """to validate farmer id."""
        serializer = ValidateFarmerIDSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)
        return comm_lib._success_response(serializer.data)
