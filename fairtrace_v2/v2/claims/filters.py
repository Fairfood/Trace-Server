"""Filters used in the app claims."""
from common import library as comm_lib
from django.db.models import Q
from django_filters import rest_framework as filters
from v2.claims.models import AttachedClaim
from v2.claims.models import Claim


class ClaimFilter(filters.FilterSet):
    """Filter for Claims."""

    supply_chain = filters.CharFilter(method="filter_supply_chain")
    search = filters.CharFilter(method="search_fields")
    type = filters.NumberFilter()
    scope = filters.NumberFilter()
    active = filters.BooleanFilter()

    class Meta:
        model = Claim
        fields = ["supply_chain", "search", "type", "scope", "active"]

    def filter_supply_chain(self, queryset, name, value):
        """To perform function ilter_supply_chain."""
        sc_id = comm_lib._decode(value)
        query = Q(supply_chains__id=sc_id)
        query |= Q(supply_chains=None)
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """To perform function search_fields."""
        return queryset.filter(name__icontains=value)


class VerificationFilter(filters.FilterSet):
    """Filter for Verifications."""

    status = filters.NumberFilter()
    supply_chain = filters.CharFilter(method="filter_supply_chain")
    claim = filters.CharFilter(method="filter_claim")
    attached_by = filters.CharFilter(method="filter_attached_by")
    verifier = filters.CharFilter(method="filter_verifier")
    type = filters.NumberFilter(method="filter_type")
    search = filters.CharFilter(method="search_fields")
    product = filters.CharFilter(method="filter_product")

    class Meta:
        model = AttachedClaim
        fields = ["status", "claim", "attached_by", "verifier", "search"]

    def filter_supply_chain(self, queryset, name, value):
        """To perform function ilter_supply_chain."""
        sc_id = comm_lib._decode(value)
        query = Q(attachedbatchclaim__batch__product__supply_chain__id=sc_id)
        return queryset.filter(query)

    def filter_claim(self, queryset, name, value):
        """To perform function ilter_claim."""
        claim_id = comm_lib._decode(value)
        query = Q(claim__id=claim_id)
        return queryset.filter(query)

    def filter_attached_by(self, queryset, name, value):
        """To perform function ilter_attached_by."""
        node_id = comm_lib._decode(value)
        query = Q(attached_by__id=node_id)
        return queryset.filter(query)

    def filter_verifier(self, queryset, name, value):
        """To perform function ilter_verifier."""
        node_id = comm_lib._decode(value)
        query = Q(verifier__id=node_id)
        return queryset.filter(query)

    def filter_type(self, queryset, name, value):
        """To perform function ilter_type."""
        query = Q(claim__type=value)
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """To perform function search_fields."""
        query = Q()
        query |= Q(attachedbatchclaim__batch__number__icontains=value)
        query |= Q(attachedbatchclaim__batch__product__name__icontains=value)
        query |= Q(attachedcompanyclaim__node__company__name__icontains=value)
        query |= Q(claim__name__icontains=value)
        query |= Q(attached_by__company__name__icontains=value)
        query |= Q(verifier__company__name__icontains=value)
        return queryset.filter(query)

    def filter_product(self, queryset, name, value):
        """To perform function ilter_product."""
        product_id = comm_lib._decode(value)
        query = Q(attachedbatchclaim__batch__product__id=product_id)
        return queryset.filter(query)
