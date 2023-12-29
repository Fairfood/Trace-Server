"""Views related to transactions in transactions app."""
import re

from common import library as comm_lib
from common.drf_custom.views import MultiPermissionView
from common.excel_templates.constants import VALUE_CHANGED
from common.excel_templates.constants import VALUE_NEW
from common.excel_templates.constants import VALUE_UNCHANGED
from common.exceptions import BadRequest
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from v2.accounts import permissions as user_permissions
from v2.products.models import Product
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.models import Farmer
from v2.transactions.bulk_upload import get_transaction_bulk_template
from v2.transactions.bulk_upload import get_transaction_bulk_template2
from v2.transactions.bulk_upload.constants import file_name
from v2.transactions.constants import BULK_UPLOAD_TYPE_TXN
from v2.transactions.constants import DUPLICATE_EX_TXN
from v2.transactions.constants import DUPLICATE_FARMER
from v2.transactions.filters import ExternalTransactionFilter
from v2.transactions.filters import InternalTransactionFilter
from v2.transactions.filters import TransactionAttachmentFilter
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import InternalTransaction
from v2.transactions.models import TransactionAttachment
from v2.transactions.serializers.external import (
    ExternalTransactionListSerializer,
)
from v2.transactions.serializers.external import (
    ExternalTransactionRejectionSerializer,
)
from v2.transactions.serializers.external import ExternalTransactionSerializer
from v2.transactions.serializers.internal import (
    InternalTransactionListSerializer,
)
from v2.transactions.serializers.internal import InternalTransactionSerializer
from v2.transactions.serializers.other import TransactionAttachmentSerializer
from v2.transactions.serializers.other import TransactionTemplateSerializer


class ExternalTransactionView(generics.ListCreateAPIView, MultiPermissionView):
    """View to list and create external transaction."""

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

    filterset_class = ExternalTransactionFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        query = Q(source=node) | Q(destination=node)
        transactions = ExternalTransaction.objects.filter(query)
        return transactions.sort_by_query_params(self.request)

    def get_serializer_class(self):
        """Fetch corresponding serializer class."""
        if self.request.method == "POST":
            return ExternalTransactionSerializer
        return ExternalTransactionListSerializer


# class CreateBulkExternalTransaction(generics.CreateAPIView):
#     """
#     API to create bulk external transactions
#     """
#
#     permission_classes = (
#         user_permissions.IsAuthenticatedWithVerifiedEmail,
#         sc_permissions.HasNodeWriteAccess)
#
#     serializer_class = BulkExternalTransactionCreate


class ExternalTransactionDetails(generics.RetrieveUpdateDestroyAPIView):
    """API to get external transaction details."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = ExternalTransactionSerializer
    queryset = ExternalTransaction.objects.all()

    def delete(self, request, *args, **kwargs):
        """To perform function lete."""
        txn = self.get_object()
        if not txn.invoice:
            raise BadRequest("Invoice not attached")
        txn.invoice = None
        txn.save()
        return comm_lib._success_response({}, "Delete successful", 200)


class RejectExternalTransaction(generics.CreateAPIView):
    """API to reject external transactions."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    serializer_class = ExternalTransactionRejectionSerializer


class InternalTransactionView(generics.ListCreateAPIView, MultiPermissionView):
    """View to list and create internal transactions."""

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

    serializer_class = InternalTransactionSerializer
    filterset_class = InternalTransactionFilter

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        transactions = InternalTransaction.objects.filter(node=node)
        return transactions.sort_by_query_params(self.request)

    def get_serializer_class(self):
        """Fetch corresponding serializer class."""
        if self.request.method == "POST":
            return InternalTransactionSerializer
        return InternalTransactionListSerializer


class InternalTransactionDetails(generics.RetrieveUpdateDestroyAPIView):
    """API to get internal transaction details."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = InternalTransactionSerializer
    queryset = InternalTransaction.objects.all()

    def delete(self, request, *args, **kwargs):
        """To perform function lete."""
        txn = self.get_object()
        if not txn.invoice:
            raise BadRequest("Invoice not attached")
        txn.invoice = None
        txn.save()
        return comm_lib._success_response({}, "Delete successful", 200)


class BulkTransactionTemplate2(APIView):
    """API to get bulk transaction template."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    @staticmethod
    def get(request, user, node, *args, **kwargs):
        """To perform function get."""
        extra_fields = request.query_params["fields"].split(",")

        product_id = request.query_params.get("product", None)
        if not product_id:
            raise BadRequest("Product ID is required in query params")
        product = Product.objects.get(id=comm_lib._decode(product_id))

        file = get_transaction_bulk_template2(
            node, product, visible_fields=extra_fields
        )

        data = HttpResponse(
            file,
            content_type="application/vnd.openxmlformats"
            + "-officedocument.spreadsheetml.sheet",
        )
        data["Content-Disposition"] = "attachment; filename=%s" % file_name
        return data

    def post(self, request, user, node, *args, **kwargs):
        """Function for validate transaction excel."""
        serializer = TransactionTemplateSerializer(
            data=request.data, context={"request": request, "view": self}
        )
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)
        serializer.save()

        return comm_lib._success_response(serializer.data)


class ValidateTransaction(generics.RetrieveAPIView):
    """View to check transaction duplicate exists."""

    @staticmethod
    def check_txn_duplicate(request):
        """To perform function check_txn_duplicate."""
        duplicate = False
        duplicate_type = ""
        transaction_status = VALUE_NEW
        duplicate_id = ""
        price_per_unit = comm_lib.convert_float(request.data["price_per_unit"])
        quantity = comm_lib.convert_float(request.data["quantity"])
        external_trans = ExternalTransaction.objects.filter(
            result_batches__product__id=comm_lib._decode(
                request.data["product_id"]
            ),
            price=price_per_unit,
            result_batches__current_quantity=quantity,
            date__date=comm_lib._string_to_datetime(
                request.data["transaction_date"]
            ),
            currency=request.data["currency"],
            source__id=comm_lib._decode(request.data["id"]),
            source__nodesupplychain__primary_operation__id=comm_lib._decode(
                request.data["primary_operation"]
            ),
        )
        if external_trans and request.data["id"]:
            duplicate = True
            duplicate_id = external_trans[0].idencode
            duplicate_type = DUPLICATE_EX_TXN
            transaction_status = VALUE_UNCHANGED
        return duplicate, duplicate_type, transaction_status, duplicate_id

    @staticmethod
    def check_farmer_duplicate(request):
        """To perform function check_farmer_duplicate."""
        duplicate = False
        duplicate_type = ""
        duplicate_id = ""
        farmer_status = VALUE_UNCHANGED
        dial_code = re.sub("[(),a-z,A-Z]", "", request.data["dial_code"])
        phone_number = str(dial_code) + str(request.data["phone"])
        farmer_dup = Farmer.objects.filter(
            first_name=request.data["first_name"],
            last_name=request.data["last_name"],
            street=request.data["street"],
            city=request.data["city"],
            country=request.data["country"],
            province=request.data["province"],
            zipcode=request.data["zipcode"],
            email=request.data["email"],
            nodesupplychain__primary_operation__id=comm_lib._decode(
                request.data["primary_operation"]
            ),
            identification_no=request.data["identification_no"],
            phone=phone_number,
        )
        if farmer_dup and not request.data["id"]:
            duplicate = True
            duplicate_type = DUPLICATE_FARMER
            duplicate_id = farmer_dup[0].idencode
            farmer_status = VALUE_NEW
        elif not request.data["id"]:
            farmer_status = VALUE_NEW
        elif not farmer_dup and request.data["id"]:
            farmer_status = VALUE_CHANGED
        return duplicate, duplicate_type, farmer_status, duplicate_id

    def post(self, request, *args, **kwargs):
        """To perform function post."""
        data = {}
        (
            data["duplicate"],
            data["duplicate_type"],
            data["farmer_status"],
            data["duplicate_id"],
        ) = self.check_farmer_duplicate(request)
        if request.data["bulk_upload_type"] == BULK_UPLOAD_TYPE_TXN:
            (
                duplicate,
                duplicate_type,
                data["transaction_status"],
                duplicate_id,
            ) = self.check_txn_duplicate(request)
            if not data["duplicate"]:
                data["duplicate"] = duplicate
                data["duplicate_id"] = duplicate_id
            if not data["duplicate_type"]:
                data["duplicate_type"] = duplicate_type
        return comm_lib._success_response(data, "Validated", 200)


class BulkTransactionTemplate(APIView):
    """API to get bulk transaction template."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    @staticmethod
    def get(request, user, node, *args, **kwargs):
        """To perform function get."""
        extra_fields = request.query_params["fields"].split(",")

        product_id = request.query_params.get("product", None)
        if not product_id:
            raise BadRequest("Product ID is required in query params")
        product = Product.objects.get(id=comm_lib._decode(product_id))

        file = get_transaction_bulk_template(
            node, product, visible_fields=extra_fields
        )

        data = HttpResponse(
            file,
            content_type="application/vnd.openxmlformats"
            + "-officedocument.spreadsheetml.sheet",
        )
        data["Content-Disposition"] = "attachment; filename=%s" % file_name
        return data

    def post(self, request, user, node, *args, **kwargs):
        """To perform function post."""
        serializer = TransactionTemplateSerializer(
            data=request.data, context={"request": request, "view": self}
        )
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)
        serializer.save()

        return comm_lib._success_response(serializer.data)


class ValidateDynamicTransaction(generics.RetrieveAPIView):
    """View to check transaction duplicate exists."""

    @staticmethod
    def check_txn_duplicate(request):
        """To perform function check_txn_duplicate."""
        try:
            product_id = comm_lib._decode(request.data.pop("product", None))
            product = Product.objects.get(id=product_id)
        except Exception:
            raise BadRequest("invalid product id")
        request.data["result_batches__product__id"] = product.id
        request.data["result_batches__product__name"] = product.name
        if "source__id" in request.data:
            request.data["source__id"] = comm_lib._decode(
                request.data["source__id"]
            )
        res = {"is_duplicate": False, "id": ""}
        external_trans = ExternalTransaction.objects.filter(**request.data)
        if external_trans:
            res["is_duplicate"] = True
            res["id"] = external_trans[0].idencode
        return res

    def post(self, request, *args, **kwargs):
        """To perform function post."""
        data = self.check_txn_duplicate(request)
        return comm_lib._success_response(data, "Validated", 200)


class TransactionAttachmentViewSet(ModelViewSet):
    """API ViewSet for managing transaction attachments.

    This ViewSet provides CRUD operations for transaction attachments.
    It includes filtering capabilities and requires authentication with
    a verified email. Additionally, it enforces node write access
    permissions.
    """

    queryset = TransactionAttachment.objects.all()
    serializer_class = TransactionAttachmentSerializer
    filterset_class = TransactionAttachmentFilter

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    def get_queryset(self):
        """Get the queryset of transaction attachments.

        This method overrides the superclass`s get_queryset method
        to filter the queryset based on query parameters provided
        in the request.

        Returns:
        - QuerySet: The filtered queryset of transaction attachments.
        """
        queryset = super(TransactionAttachmentViewSet, self).get_queryset()
        return queryset.filter_by_query_params(self.request)

    def create(self, request, *args, **kwargs):
        """Create a new transaction attachment.

        This method overrides the superclass`s create method and
        injects the node information into the request before
        calling the superclass`s create method.

        Parameters:
        - request: The HTTP request object.
        - args: Additional positional arguments.
        - kwargs: Additional keyword arguments.

        Returns:
        - Response: The response of the create operation.
        """
        self.inject_node(request)
        return super(TransactionAttachmentViewSet, self).create(
            request, *args, **kwargs
        )

    def update(self, request, *args, **kwargs):
        """Update an existing transaction attachment.

        This method overrides the superclass`s update method and
        injects the node information into the request before
        calling the superclass`s update method.

        Parameters:
        - request: The HTTP request object.
        - args: Additional positional arguments.
        - kwargs: Additional keyword arguments.

        Returns:
        - Response: The response of the update operation.
        """
        self.inject_node(request)
        return super(TransactionAttachmentViewSet, self).update(
            request, *args, **kwargs
        )

    @staticmethod
    def inject_node(request):
        """Add node to the request data."""
        node = request.parser_context["kwargs"].get("node", None)
        set_mutable = False

        # Check for mutable flag present for request data.
        if hasattr(request.data, "_mutable"):
            set_mutable = True

        if set_mutable:
            mutable = request.data._mutable
            # set data as mutable
            request.data._mutable = True
            request.data["node"] = node.idencode
            # restore to original
            request.data._mutable = mutable
        else:
            request.data["node"] = node
