"""Filters used in the app bulk_templates."""
from django.db.models import Q
from django_filters import rest_framework as filters
from v2.bulk_templates.models import Template


class TemplateFilter(filters.FilterSet):
    """Filter for Template."""

    name = filters.CharFilter(method="filter_name")

    class Meta:
        model = Template
        fields = ["name"]

    def filter_name(self, queryset, name, value):
        """To perform function ilter_name."""
        value = value.capitalize()
        query = Q(name__contains=value)
        return queryset.filter(query)
