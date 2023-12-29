"""View for transactions details related APIs."""

from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response

from common import library as comm_lib
from common.exceptions import AccessForbidden, BadRequest, UnauthorizedAccess
from . import check_node
from v2.accounts import permissions as user_permissions
from v2.products.models import Batch
from v2.products.serializers import batch as batch_serializers
from v2.projects import filters
from v2.projects.models import NodeCard
from v2.projects.models import Project
from v2.projects.serializers import transactions
from v2.supply_chains import permissions as sc_permissions
from v2.transactions import constants as trans_constants
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import Transaction


class AppTransactionAPI(generics.ListCreateAPIView):
    """Class to handle AppTransactionAPI and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )

    # filterset_class = filters.FilterTransactions
    serializer_class = transactions.AppTransactionSerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        user = self.kwargs["user"]
        query = Q(source=node) | Q(destination=node)
        return ExternalTransaction.objects.filter(query).filter(creator=user)


class TransactionInvoiceAPI(generics.RetrieveUpdateAPIView):
    """Class to handle TransactionInvoiceAPI and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = transactions.TransactionInvoiceSerializer

    def get_serializer_context(self):
        """Overriding method to log."""
        comm_lib._encode(self.kwargs["pk"])
        return super(TransactionInvoiceAPI, self).get_serializer_context()

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        query = Q(source=node) | Q(destination=node)
        return ExternalTransaction.objects.filter(query)

class OpenTransactionAPI(generics.ListAPIView):
    """View for list transaction details of particular farmer.

    The farmer id is passing through params.
    """

    permission_classes = (user_permissions.OpenValidTOTP,)

    serializer_class = transactions.OpenTransactionSerializer
    filterset_class = filters.OpenFilterTransactions

    def get_queryset(self):
        """To perform function get_queryset."""
        card_id = self.request.query_params.get("card_id", None)
        fair_id = card_id.upper().lstrip("FF").replace(" ", "")
        node_card = NodeCard.objects.filter(fairid__iexact=fair_id).first()
        if not node_card:
            raise BadRequest("Invalid card number")
        if not node_card.node:
            raise BadRequest("Invalid card number")
        node = node_card.node
        check_node(self.request, node)

        query = Q(source__id=node.id) | Q(destination__id=node.id)
        return ExternalTransaction.objects.filter(query).order_by("-date")


class OpenTransactionDetails(generics.ListAPIView):
    """View for transaction details."""

    permission_classes = (user_permissions.OpenValidTOTP,)
    serializer_class = transactions.OpenTransactionDetailsSerializer

    def get(self, request, *args, **kwargs):
        """function for get the details of transaction.

        and here transaction id in encrypted format. so decrypt id
        before filter Transaction.
        """
        trans_id = kwargs["pk"]
        try:
            transaction = ExternalTransaction.objects.get(
                id=int(comm_lib._decrypt(trans_id))
            )
        except Exception:
            raise BadRequest("Invalid Transaction id.")
        check_node(self.request, transaction.source)

        serializer = transactions.OpenTransactionDetailsSerializer(
            transaction, data=request.data, partial=True, context=self.kwargs
        )
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)
        return Response(serializer.data)


class AppSentTransactionAPI(generics.CreateAPIView):
    """View for create sent transaction."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )
    serializer_class = transactions.AppSentTransactionSerializer


class AppTransactionListAPI(generics.ListAPIView):
    """View for list transaction."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )
    filterset_class = filters.FilterTransactions
    serializer_class = transactions.AppTransactionListSerializer

    def get(self, request, *args, **kwargs):
        """To perform function get."""
        project_id = request.GET.get("project_id", None)
        node = self.kwargs["node"]
        if project_id:
            try:
                project = Project.objects.get(pk=comm_lib._decode(project_id))
                suppliers = list(
                    node.get_suppliers(
                        supply_chain=project.supply_chain
                    ).values_list("id", flat=True)
                )
                buyers = list(
                    node.get_buyers(
                        supply_chain=project.supply_chain
                    ).values_list("id", flat=True)
                )
                node_list = suppliers + buyers
                self.member_nodes = project.member_nodes.filter(
                    id__in=node_list
                ).values_list("id", flat=True)
            except Project.DoesNotExist:
                self.member_nodes = []
        return super(AppTransactionListAPI, self).get(request, *args, **kwargs)

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        user = self.kwargs["user"]
        query = self._construct_query(node, user)
        return Transaction.objects.filter(query).filter(creator=user)

    def _construct_query(self, node, user):
        """To perform function _construct_query."""
        if not hasattr(self, "member_nodes"):
            self.member_nodes = []
        if self.member_nodes:
            member_nodes = self.member_nodes
            query = Q(
                externaltransaction__source=node,
                externaltransaction__destination_id__in=member_nodes,
            ) | Q(
                externaltransaction__destination=node,
                externaltransaction__source_id__in=member_nodes,
            )
        else:
            query = Q(externaltransaction__source=node) | Q(
                externaltransaction__destination=node
            )

        query |= Q(internaltransaction__node=node) & Q(
            internaltransaction__type=trans_constants.INTERNAL_TRANS_TYPE_LOSS
        )
        query &= Q(client_type=trans_constants.CLIENT_APP)
        return query


class AppBatchDetails(generics.ListAPIView):
    """API to get batch details owned by the user with updated datetime
    filter."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    filterset_class = filters.FilterBatch
    serializer_class = batch_serializers.BatchDetailSerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        _type = trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
        return Batch.objects.filter(
            creator=self.kwargs["user"],
            node=self.kwargs["node"],
            source_transaction__externaltransaction__type=_type,
        )
