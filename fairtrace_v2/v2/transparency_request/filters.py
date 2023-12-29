"""Filters used in the traceability requests app."""
from common import library as comm_lib
from django.db.models import Q
from django.utils.timezone import datetime
from django_filters import rest_framework as filters
from v2.products.models import Product
from v2.supply_chains.models import Node
from v2.supply_chains.models import SupplyChain
from v2.transparency_request.models import StockRequest

from . import constants
from .models import TransparencyRequest


class StockRequestFilter(filters.FilterSet):
    """Filter for StockRequest.

    Over-ridden to search requester and requester full names,
    irrespective of whether it is farmer or company.
    """

    type = filters.NumberFilter(method="filter_type")
    node = filters.CharFilter(method="filter_node")
    product = filters.CharFilter(method="filter_product")
    supply_chain = filters.CharFilter(method="filter_supply_chain")
    status = filters.NumberFilter()
    search = filters.CharFilter(method="search_tr")
    date_from = filters.CharFilter(method="filter_date_from")
    date_to = filters.CharFilter(method="filter_date_to")
    date_on = filters.CharFilter(method="filter_date_on")
    quantity_from = filters.NumberFilter(
        field_name="quantity", lookup_expr="gt"
    )
    quantity_to = filters.NumberFilter(field_name="quantity", lookup_expr="lt")
    quantity_is = filters.CharFilter(method="filter_quantity_is")

    class Meta:
        model = StockRequest
        fields = [
            "search",
        ]

    def filter_type(self, queryset, name, value):
        """Search with value."""
        current_node = self.request.parser_context["kwargs"]["node"]
        if value == constants.TRANSPARENCY_REQUEST_DIRECTION_INCOMING:
            query = Q(requestee=current_node)
        else:
            query = Q(requester=current_node)
        return queryset.filter(query)

    def filter_node(self, queryset, name, value):
        """Search with value."""
        node = Node.objects.get(id=comm_lib._decode(value))
        query = Q(requester=node) | Q(requestee=node)
        return queryset.filter(query)

    def filter_product(self, queryset, name, value):
        """Search with value."""
        product = Product.objects.get(id=comm_lib._decode(value))
        return queryset.filter(product=product)

    def filter_supply_chain(self, queryset, name, value):
        """Search with value."""
        product = SupplyChain.objects.get(id=comm_lib._decode(value))
        return queryset.filter(product__supply_chain=product)

    def search_tr(self, queryset, name, value):
        """Search with value."""
        requester_company = Q(requester__company__name__icontains=value)
        requester_farmer = Q(
            requester__farmer__first_name__icontains=value
        ) | Q(requester__farmer__last_name__icontains=value)
        requester_query = requester_company | requester_farmer

        requestee_company = Q(requestee__company__name__icontains=value)
        requestee_farmer = Q(
            requestee__farmer__first_name__icontains=value
        ) | Q(requestee__farmer__last_name__icontains=value)
        requestee_query = requestee_company | requestee_farmer

        product_query = Q(product__name__icontains=value)

        number_query = Q(number__icontains=value)
        query = (
            requester_query | requestee_query | product_query | number_query
        )

        return queryset.filter(query)

    def filter_date_from(self, queryset, name, value):
        """Search with value."""
        value += "-00:00:00"
        value = datetime.strptime(value, "%d/%m/%Y-%H:%M:%S")
        query = Q(created_on__gt=value)
        return queryset.filter(query)

    def filter_date_to(self, queryset, name, value):
        """Search with value."""
        value += "-23:59:59"
        value = datetime.strptime(value, "%d/%m/%Y-%H:%M:%S")
        query = Q(created_on__lt=value)
        return queryset.filter(query)

    def filter_date_on(self, queryset, name, value):
        """Search with value."""
        value += "-00:00:00"
        value = datetime.strptime(value, "%d/%m/%Y-%H:%M:%S")
        query = Q(created_on=value)
        return queryset.filter(query)

    def filter_quantity_is(self, queryset, name, value):
        """Search with value."""
        query = Q(quantity=value)
        return queryset.filter(query)


class TransparencyRequestFilter(filters.FilterSet):
    """Filter for transparency Request."""

    type = filters.NumberFilter(method="filter_type")
    request_type = filters.NumberFilter(method="filter_request_type")
    status = filters.NumberFilter()
    search = filters.CharFilter(method="search_rq")

    class Meta:
        model = TransparencyRequest
        fields = ["search", "type", "request_type", "status"]

    def filter_type(self, queryset, name, value):
        """Search with value."""
        current_node = self.request.parser_context["kwargs"]["node"]
        if value == constants.TRANSPARENCY_REQUEST_DIRECTION_INCOMING:
            query = Q(requestee=current_node)
        else:
            query = Q(requester=current_node)
        return queryset.filter(query)

    def filter_request_type(self, queryset, name, value):
        """Search with value."""
        if value == constants.TRANSPARENCY_REQUEST_TYPE_CLAIM:
            query = Q(request_type=constants.TRANSPARENCY_REQUEST_TYPE_CLAIM)
        elif value == constants.TRANSPARENCY_REQUEST_TYPE_TRANSACTION:
            query = Q(
                request_type=constants.TRANSPARENCY_REQUEST_TYPE_TRANSACTION
            )
        elif value == constants.TRANSPARENCY_REQUEST_TYPE_INFORMATION:
            query = Q(
                request_type=constants.TRANSPARENCY_REQUEST_TYPE_INFORMATION
            )
        else:
            query = Q(
                request_type=constants.TRANSPARENCY_REQUEST_TYPE_CONNECTION
            )
        return queryset.filter(query)

    def search_rq(self, queryset, name, value):
        """Search with value."""
        requester_company = Q(requester__company__name__icontains=value)
        requester_member = Q(
            requester__members__first_name__icontains=value
        ) | Q(requester__members__last_name__icontains=value)
        requester_query = requester_company | requester_member
        supplier_company = Q(requestee__company__name__icontains=value)
        supplier_member = Q(
            requestee__members__first_name__icontains=value
        ) | Q(requestee__members__first_name__icontains=value)
        supplier_query = supplier_company | supplier_member
        number_query = Q(number__icontains=value)

        query = requester_query | supplier_query | number_query

        return queryset.filter(query).order_by("-id").distinct("id")
