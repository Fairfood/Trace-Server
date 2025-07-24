"""Managers to add more functionalities to Model.objects."""
from common.library import decode
from django.db import models
from django.db.models import Count
from django.db.models import Q
from django.db.models import Sum
from django.db.models import Value
from django.db.models.functions import Trunc
from v2.products.constants import PRODUCT_TYPE_CARBON
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.constants import NODE_TYPE_FARM


class ExternalTransactionQuerySet(models.QuerySet):
    """Class to handle ExternalTransactionQuerySet and functions."""

    def sort_by_query_params(self, request):
        """To perform function sort_by_query_params."""
        queryset = self
        sort_by = request.query_params.get("sort_by", None)
        order_by = request.query_params.get("order_by", "asc")
        field_set = (
            "number", "connection.name", "date", "quantity", "type", "product",
            "source", "receiver", "blockChain"
        )
        if sort_by:
            sort_by = sort_by.strip()
            if sort_by in field_set:
                sort_by = self._clean_field(sort_by)
                if order_by.lower().strip() == "desc":
                    sort_by = f"-{sort_by}"
                return queryset.order_by(sort_by)
        return queryset

    def filter_queryset(self, request):
        """To perform function ilter_queryset."""
        queryset = self

        start_date = request.query_params.get("start_date", None)
        end_date = request.query_params.get("end_date", None)
        supply_chain = request.query_params.get("supply_chain", None)
        product = request.query_params.get("product", None)

        if start_date:
            queryset = queryset.filter(date__gt=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if supply_chain:
            supply_chain_id = decode(supply_chain)
            queryset = queryset.filter(
                Q(source_batches__product__supply_chain__id=supply_chain_id)
                | Q(result_batches__product__supply_chain__id=supply_chain_id)
            )
        if product:
            product_id = decode(product)
            queryset = queryset.filter(
                Q(source_batches__product__id=product_id)
                | Q(result_batches__product__id=product_id)
            )
        return queryset

    @staticmethod
    def _clean_field(sort_by):
        """To perform function _clean_field."""

        filter_fields = {
            "product": "source_batches__product__name",
            "sender": "source__full_name",
            "receiver": "destination__full_name",
            "quantity": "source_batches__initial_quantity",
            "blockChain": "blockchain_address",
        }
        if "." in sort_by:
            sort_by = sort_by.replace(".", "__")
            if sort_by.split("__")[0] == "connection":
                sort_by = sort_by.replace("connection", "destination")
        # if sort_by.split("__")[0] == "quantity":
        #     sort_by = "result_batches__initial_quantity_in_gram"
        if sort_by in filter_fields:
            sort_by = filter_fields[sort_by]
        return sort_by

    def group_count_with_date(self, trunc_type="month", extra_fields=()):
        """Grouping queryset with created_on and extra_fields.

        * extra_fields -> Should be direct fields and the count will be
                effected by these fields.
        * trunc_type -> Options month/week/day/quarter/year
        """
        queryset = self.annotate(
            truncated_by=Value(trunc_type, output_field=models.CharField()),
            grouped_by=Trunc("date", kind=trunc_type),
        )
        return (
            queryset.values("truncated_by", "grouped_by", *extra_fields)
            .annotate(count=Count("grouped_by"))
            .order_by("grouped_by")
        )

    def group_quantity_with_created_on(
        self, trunc_type="month", extra_fields=()
    ):
        """Grouping queryset with created_on and extra_fields. A total of
        quantity is returned with each item.

        * extra_fields -> Should be direct fields and the count will be
                effected by these fields.
        * trunc_type -> Options month/week/day/quarter/year
        """
        queryset = self.annotate(
            truncated_by=Value(trunc_type, output_field=models.CharField()),
            grouped_by=Trunc("date", kind=trunc_type),
        )
        return (
            queryset.values("truncated_by", "grouped_by", *extra_fields)
            .annotate(total_quantity=Sum("_source_quantity"))
            .order_by("grouped_by")
        )

    def sourced_from_farmers(self):
        """Only returns Transactions sourced from farmers."""
        return self.filter(source__type=NODE_TYPE_FARM)

    def sourced_from_company(self):
        """Only returns Transactions sourced from companies."""
        return self.filter(source__type=NODE_TYPE_COMPANY)

    def exclude_test(self):
        """Exclude test nodes."""
        return self.filter(
            Q(source__is_test=False) | Q(destination__is_test=False)
        )
    
    def exclude_carbon_transactions(self):
        """Exclude carbon transactions"""
        query = Q(source_batches__product__type=PRODUCT_TYPE_CARBON) | Q(
            result_batches__product__type=PRODUCT_TYPE_CARBON
        )
        return self.exclude(query)


class InternalTransactionQuerySet(models.QuerySet):
    """Class to handle InternalTransactionQuerySet and functions."""

    def sort_by_query_params(self, request):
        """To perform function sort_by_query_params."""
        queryset = self
        sort_by = request.query_params.get("sort_by", None)
        order_by = request.query_params.get("order_by", "asc")
        field_set = ("number", "source_quantity", "date", "type")
        if sort_by:
            sort_by = sort_by.strip()
            if sort_by in field_set:
                sort_by = self._clean_field(sort_by)
                if order_by.lower().strip() == "desc":
                    sort_by = f"-{sort_by}"
                return queryset.order_by(sort_by)
        return queryset

    @staticmethod
    def _clean_field(sort_by):
        """To perform function _clean_field."""
        if "." in sort_by:
            sort_by = sort_by.replace(".", "__")
            if sort_by.split("__")[0] == "connection":
                sort_by = sort_by.replace("connection", "destination")
        if sort_by.split("__")[0] == "source_quantity":
            sort_by = "_source_quantity"
        return sort_by


class TransactionAttachmentQuerySet(models.QuerySet):
    """Class to handle TransactionAttachmentQuerySet and functions."""

    def only_node_involved_attachments(self, node):
        """Return only node involved transaction attachments."""
        queryset = self
        return queryset.filter(
            Q(transaction__externaltransaction__source=node)
            | Q(transaction__externaltransaction__destination=node)
            | Q(transaction__internaltransaction__node=node)
        )

    def filter_by_query_params(self, request):
        """filter with request params."""
        queryset = self
        node = request.parser_context["kwargs"].get("node", None)
        if node:
            queryset = queryset.only_node_involved_attachments(node)
        return queryset
