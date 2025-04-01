"""Filters used in the app products."""

from common import library as comm_lib
from common.library import decode
from django.db.models import Case, F, Q, When
from django.utils.timezone import datetime
from django_filters import rest_framework as filters
from v2.claims import constants as claim_constants
from v2.products.models import Batch, BatchFarmerMapping, Product
from v2.transactions.constants import (EXTERNAL_TRANS_TYPE_REVERSAL,
                                       INTERNAL_TRANS_TYPE_MERGE,
                                       INTERNAL_TRANS_TYPE_PROCESSING,
                                       TRANSACTION_TYPE_EXTERNAL,
                                       TRANSACTION_TYPE_INTERNAL)


class ProductFilter(filters.FilterSet):
    """Filter for Products.

    Over-ridden to accommodate supplychain
    """

    supply_chain = filters.CharFilter(method="filter_supply_chain")
    search = filters.CharFilter(method="search_fields")

    class Meta:
        model = Product
        fields = ["supply_chain", "search"]

    def filter_supply_chain(self, queryset, name, value):
        """To perform function ilter_supply_chain."""
        sc_ids = [comm_lib._decode(i) for i in value.split(",")]
        query = Q(supply_chain__id__in=sc_ids)
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """To perform function search_fields."""
        return queryset.filter(name__icontains=value)


class BatchFilter(filters.FilterSet):
    """Filter for Batches.

    Over-ridden to accommodate supplychain
    """

    def __init__(self, node=None, **kwargs):
        """To perform function __init__."""
        super().__init__(**kwargs)
        if "archived" not in self.data:
            if hasattr(self.data, "_mutable"):
                self.data._mutable = True
                self.data["archived"] = "false"
                self.data._mutable = False
            else:
                self.data["archived"] = "false"
        if not node:
            self.node = self.request.parser_context["kwargs"]["node"]
        else:
            self.node = node

    supply_chain = filters.CharFilter(method="filter_supply_chain")
    product = filters.CharFilter(method="filter_by_product")
    search = filters.CharFilter(method="search_fields")
    supplier = filters.CharFilter(method="filter_by_supplier")
    claim = filters.CharFilter(method="filter_by_claims")
    claims = filters.CharFilter(method="filter_by_claims")
    date_from = filters.CharFilter(method="filter_date_from")
    date_to = filters.CharFilter(method="filter_date_to")
    date_on = filters.CharFilter(method="filter_date_on")
    created_from = filters.CharFilter(method="filter_created_from")
    quantity_from = filters.NumberFilter(
        field_name="current_quantity", lookup_expr="gte"
    )
    quantity_to = filters.NumberFilter(field_name="current_quantity", lookup_expr="lte")
    quantity_is = filters.CharFilter(method="filter_quantity_is")

    class Meta:
        model = Batch
        fields = ["supply_chain", "search", "archived"]

    def filter_by_supplier(self, queryset, name, value):
        """To perform function ilter_by_supplier."""
        node_id = comm_lib._decode(value)

        return (
            queryset.filter(source_transaction__isnull=False)
            .annotate(
                supplier_id=Case(
                    When(
                        Q(
                            source_transaction__transaction_type=TRANSACTION_TYPE_EXTERNAL
                        ),
                        then=F("source_transaction__externaltransaction__source__id"),
                    ),
                    default=F("source_transaction__internaltransaction__node__id"),
                )
            )
            .filter(supplier_id=node_id)
        )

    def filter_by_product(self, queryset, name, value):
        """To perform function ilter_by_product."""
        product_id = comm_lib._decode(value)
        query = Q(product__id=product_id)
        return queryset.filter(query)

    def filter_by_claims(self, queryset, name, value):
        """To perform function ilter_by_claims."""
        claims = []
        for val in value.split(","):
            claim_id = comm_lib._decode(val)
            claims.append(claim_id)
        queryset = queryset.filter(
            claims__claim__id__in=claims,
            claims__status=claim_constants.STATUS_APPROVED,
        )
        return queryset

    def filter_supply_chain(self, queryset, name, value):
        """To perform function ilter_supply_chain."""
        sc_id = comm_lib._decode(value)
        query = Q(product__supply_chain__id=sc_id)
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """To perform function search_fields."""
        query = Q()
        query |= Q(name__icontains=value)
        query |= Q(product__name__icontains=value)
        query |= Q(number__icontains=value)
        query |= Q(buyer_ref_number__icontains=value)
        query |= Q(seller_ref_number__icontains=value)
        return queryset.filter(query)

    def filter_date_from(self, queryset, name, value):
        """To perform function ilter_date_from."""
        value += "-00:00:00"
        value = datetime.strptime(value, "%d/%m/%Y-%H:%M:%S")
        query = Q(source_transaction__created_on__gte=value)
        return queryset.filter(query)

    def filter_date_to(self, queryset, name, value):
        """To perform function ilter_date_to."""
        value += "-23:59:59"
        value = datetime.strptime(value, "%d/%m/%Y-%H:%M:%S")
        query = Q(source_transaction__created_on__lte=value)
        return queryset.filter(query)

    def filter_date_on(self, queryset, name, value):
        """To perform function ilter_date_on."""
        value = datetime.strptime(value, "%d/%m/%Y")
        query = Q(source_transaction__created_on__contains=value.date())
        return queryset.filter(query)

    def filter_created_from(self, queryset, name, value):
        """To perform function ilter_created_from."""
        value = value.lower()
        query = Q()
        ext = EXTERNAL_TRANS_TYPE_REVERSAL
        mer = INTERNAL_TRANS_TYPE_MERGE
        pro = INTERNAL_TRANS_TYPE_PROCESSING
        if value in ["returned", "purchased"]:
            query &= Q(source_transaction__transaction_type=TRANSACTION_TYPE_EXTERNAL)
            if value == "returned":
                query &= Q(source_transaction__externaltransaction__type=ext)
            else:
                query &= ~Q(source_transaction__externaltransaction__type=ext)
        elif value in ["merged", "processed"]:
            query &= Q(source_transaction__transaction_type=TRANSACTION_TYPE_INTERNAL)
            if value == "merged":
                query &= Q(source_transaction__internaltransaction__type=mer)
            else:
                query &= Q(source_transaction__internaltransaction__type=pro)
        return queryset.filter(query)

    def filter_quantity_is(self, queryset, name, value):
        """To perform function ilter_quantity_is."""
        query = Q(current_quantity=value)
        return queryset.filter(query)


class BatchFarmerMappingFilter(filters.FilterSet):
    """Filter class for filtering BatchFarmerMapping instances.

    This filter class provides filtering options based on batch and
    farmer fields. It allows filtering BatchFarmerMapping instances
    based on the batch ID and farmer ID.
    """

    batch = filters.CharFilter(method="filter_by_batch")
    farmer = filters.CharFilter(method="filter_by_farmer")

    class Meta:
        model = BatchFarmerMapping
        fields = ["batch", "farmer"]

    def filter_by_batch(self, queryset, name, value):
        """Filter BatchFarmerMapping instances by batch ID.

        Parameters:
        - queryset: The queryset to filter.
        - name: The name of the filter field.
        - value: The value to filter with.

        Returns:
        - QuerySet: The filtered queryset based on the batch ID.
        """
        pk = decode(value)
        return queryset.filter(batch_id=pk)

    def filter_by_farmer(self, queryset, name, value):
        """Filter BatchFarmerMapping instances by farmer ID.

        Parameters:
        - queryset: The queryset to filter.
        - name: The name of the filter field.
        - value: The value to filter with.

        Returns:
        - QuerySet: The filtered queryset based on the farmer ID.
        """
        pk = decode(value)
        return queryset.filter(farmer_id=pk)
