"""Filters used in the app products."""
from common import library as comm_lib
from django.db.models import Q
from django_filters import rest_framework as filters
from v2.communications.models import Notification


class NotificationFilter(filters.FilterSet):
    """Filter for Notifications."""

    node = filters.CharFilter(method="filter_actor")
    search = filters.CharFilter(method="search_fields")

    class Meta:
        model = Notification
        fields = ["node", "search"]

    def filter_actor(self, queryset, name, value):
        """Filter queryset."""
        node_ids = [comm_lib._decode(i) for i in value.split(",")]
        query = Q(target_node__id__in=node_ids)
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """Filter queryset."""
        return queryset.filter(title_en__icontains=value)
