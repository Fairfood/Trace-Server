"""Filters used in the app projects."""
from common import library as comm_lib
from common.library import _unix_to_datetime
from django.db.models import Q
from django_filters import rest_framework as filters
from v2.transactions.constants import TRANSACTION_TYPE_EXTERNAL


class FilterNodes(filters.FilterSet):
    """Filter to filter buyers and suppliers by updated time."""

    updated_after = filters.NumberFilter(method="get_nodes_updated_after")

    def get_nodes_updated_after(self, queryset, name, value):
        """Get nodes updated_after."""
        dt = _unix_to_datetime(value)
        query = Q()
        query |= Q(updated_on__gte=dt)
        query |= Q(cards__created_on__gte=dt)
        return queryset.filter(query).distinct()


class FilterCards(filters.FilterSet):
    """To filter by node."""

    node = filters.CharFilter(method="get_node_cards")
    status = filters.NumberFilter()

    def get_node_cards(self, queryset, name, value):
        """Get node cards."""
        return queryset.filter(node__id=comm_lib._decode(value))


class OpenFilterTransactions(filters.FilterSet):
    """Filter to filter transactions by updated time."""

    start_date = filters.NumberFilter(method="get_transactions_start_date")
    end_date = filters.NumberFilter(method="get_transactions_end_date")

    def get_transactions_start_date(self, queryset, name, value):
        """Get transactions start_date_date."""
        dt = _unix_to_datetime(value)
        return queryset.filter(created_on__gte=dt)

    def get_transactions_end_date(self, queryset, name, value):
        """Get transactions end_date."""
        dt = _unix_to_datetime(value)
        return queryset.filter(created_on__lte=dt)


class FilterTransactions(filters.FilterSet):
    """Filter to filter transactions by updated time."""

    updated_after = filters.NumberFilter(
        method="get_transactions_updated_after"
    )
    updated_before = filters.NumberFilter(
        method="get_transactions_updated_before"
    )
    only_quantity_available = filters.CharFilter(
        method="get_transactions_quantity_available"
    )

    def get_transactions_updated_after(self, queryset, name, value):
        """Get transactions updated_after."""
        dt = _unix_to_datetime(value)
        return queryset.filter(created_on__gte=dt)

    def get_transactions_updated_before(self, queryset, name, value):
        """Get transactions updated_before."""
        dt = _unix_to_datetime(value)
        return queryset.filter(created_on__lt=dt)

    def get_transactions_quantity_available(self, queryset, name, value):
        """Get transactions quantity_available."""
        if value == "true":

            # only buy transactions required.
            try:
                node = self.request.parser_context["kwargs"]["node"]
                extra = {"externaltransaction__destination": node}
            except KeyError:
                extra = {}

            return queryset.filter(
                transaction_type=TRANSACTION_TYPE_EXTERNAL,
                **extra,
                result_batches__current_quantity__gt=0
            )
        return queryset


class FilterBatch(filters.FilterSet):
    """Filter to filter batch by updated time."""

    updated_after = filters.NumberFilter(method="get_batch_updated_after")
    updated_before = filters.NumberFilter(method="get_batch_updated_before")
    only_quantity_available = filters.CharFilter(
        method="get_batch_quantity_available"
    )

    def get_batch_updated_after(self, queryset, name, value):
        """Get batch updated_after."""
        dt = _unix_to_datetime(value)
        return queryset.filter(updated_on__gte=dt)

    def get_batch_updated_before(self, queryset, name, value):
        """Get batch updated_before."""
        dt = _unix_to_datetime(value)
        return queryset.filter(updated_on__lt=dt)

    def get_batch_quantity_available(self, queryset, name, value):
        """Get batch quantity_available."""
        if value == "true":
            return queryset.filter(current_quantity__gt=0)
        return queryset
