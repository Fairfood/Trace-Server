"""Filters used in the app transactions."""
from common import library as comm_lib
from django_filters import rest_framework as filters
from v2.dashboard.models import CITheme


class CIThemeFilter(filters.FilterSet):
    """Class to handle CIThemeFilter and functions."""

    supply_chain = filters.CharFilter(method="filter_supply_chain")

    class Meta:
        model = CITheme
        fields = ["supply_chain"]

    def filter_supply_chain(self, queryset, name, value):
        """To perform function ilter_supply_chain."""
        sc_id = comm_lib._decode(value)
        return queryset.filter(supply_chains=sc_id)
