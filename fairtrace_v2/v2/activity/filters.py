"""Filters used in the activity app."""
from common import library as comm_lib
from django_filters import rest_framework as filters
from v2.activity.models import Activity


class ActivityFilter(filters.FilterSet):
    """Filter for Activities."""

    supply_chain = filters.CharFilter(method="filter_supply_chain")

    class Meta:
        model = Activity
        fields = [
            "supply_chain",
        ]

    def filter_supply_chain(self, queryset, name, value):
        """To perform function ilter_supply_chain."""
        sc_id = comm_lib._decode(value)
        return queryset.filter(supply_chain__id=sc_id)
