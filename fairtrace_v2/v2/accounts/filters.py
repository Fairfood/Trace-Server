"""Filters used in the app accounts."""
from django.db.models import Q
from django_filters import rest_framework as filters
from v2.accounts.models import FairfoodUser


class UserFilter(filters.FilterSet):
    """Filter for FairfoodUser."""

    email = filters.CharFilter()
    type = filters.CharFilter()
    is_active = filters.BooleanFilter()
    search = filters.CharFilter(method="search_fields")

    class Meta:
        model = FairfoodUser
        fields = ["email", "type", "is_active"]

    @staticmethod
    def search_fields(queryset, name, value):
        """Search within the name fields."""
        return queryset.filter(
            Q(first_name__icontains=value) | Q(last_name__icontains=value)
        )
