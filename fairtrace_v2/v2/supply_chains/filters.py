"""Filters used in the app supply_chains."""
from common import library as comm_lib
from common.library import decode
from django.db.models import Q
from django_filters import rest_framework as filters
from v2.claims.constants import STATUS_APPROVED
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Label
from v2.supply_chains.models import Node
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.models import SupplyChain


class FarmerFilter(filters.FilterSet):
    """Filter for Products.

    Over-ridden to accommodate supplychain
    """

    supply_chain = filters.CharFilter(method="filter_supply_chain")
    search = filters.CharFilter(method="search_fields")
    country = filters.CharFilter(method="filter_country")
    is_test = filters.CharFilter(method="filter_is_test")

    class Meta:
        model = Farmer
        fields = ["supply_chain", "search", "country", "is_test"]

    def filter_supply_chain(self, queryset, name, value):
        """Filter with value."""
        sc_id = comm_lib._decode(value)
        query = Q(supply_chains__id=sc_id)
        return queryset.filter(query)

    def filter_country(self, queryset, name, value):
        """Filter with value."""
        query = Q(country__icontains=value)
        return queryset.filter(query)

    def filter_is_test(self, queryset, name, value):
        """Filter with value."""
        if value == "true":
            query = Q(is_test=True)
        elif value == "false":
            query = Q(is_test=False)
        else:
            query = Q()
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """Search with value."""
        query = Q()
        query |= Q(first_name__icontains=value)
        query |= Q(last_name__icontains=value)
        return queryset.filter(query)


class NodeFilter(filters.FilterSet):
    """Filter for Nodes.

    filer by name and type
    """

    type = filters.NumberFilter()
    search = filters.CharFilter(method="search_fields")
    claims = filters.CharFilter(method="filter_by_claims")
    name = filters.CharFilter(method="search_fields")
    country = filters.CharFilter(method="filter_by_country")
    province = filters.CharFilter(method="filter_by_province")
    location_type = filters.CharFilter(method="filter_by_location_type")
    connection = filters.CharFilter(method="filter_by_connection")

    class Meta:
        model = Node
        fields = [
            "type", "search", "name", "country", "province", 
            "location_type", "connection"
        ]

    def filter_by_claims(self, queryset, name, value):
        """Filter with value."""
        for val in value.split(","):
            claim_id = comm_lib._decode(val)
            queryset = queryset.filter(
                claims__claim__id=claim_id, claims__status=STATUS_APPROVED
            )
        return queryset

    def filter_by_name(self, queryset, name, value):
        """Filter with value."""
        query = Q(company__name__icontains=value)
        return queryset.filter(query)
    
    def filter_by_country(self, queryset, name, value):
        """Filter with value."""
        query = Q(farmer__country__iexact=value)
        return queryset.filter(query)

    def filter_by_province(self, queryset, name, value):
        """Filter with value."""
        query = Q(farmer__province__iexact=value)
        return queryset.filter(query)

    def filter_by_location_type(self, queryset, name, value):
        """Filter with value."""
        query = Q(farmer__plots__location_type__iexact=value)
        return queryset.filter(query)

    def filter_by_connection(self, queryset, name, value):
        """Filter with value."""
        operation_id = comm_lib._decode(value)
        query = Q(primary_operation__id=operation_id)
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """Filter with value."""
        query = Q()
        query |= Q(farmer__first_name__icontains=value)
        query |= Q(farmer__last_name__icontains=value)
        query |= Q(farmer__email__icontains=value)
        query |= Q(farmer__street__icontains=value)
        query |= Q(farmer__city__icontains=value)
        query |= Q(farmer__sub_province__icontains=value)
        query |= Q(farmer__province__icontains=value)
        query |= Q(farmer__country__icontains=value)
        query |= Q(company__name__icontains=value)
        query |= Q(farmer__farmer_references__number__icontains=value)
        return queryset.filter(query)


class NodeSupplyChainFilter(filters.FilterSet):
    """Filter for Node supply chain.filer by supply chain and node."""

    supply_chain = filters.CharFilter(method="filter_supply_chain")
    node = filters.CharFilter(method="filter_node")
    search = filters.CharFilter(method="search_fields")

    class Meta:
        model = NodeSupplyChain
        fields = ["supply_chain", "node", "search"]

    def filter_supply_chain(self, queryset, name, value):
        """Filter with value."""
        """Filter with value."""
        sc_id = comm_lib._decode(value)
        query = Q(supply_chain__id=sc_id)
        return queryset.filter(query)

    def filter_node(self, queryset, name, value):
        """Filter with value."""
        """Filter with value."""
        node_id = comm_lib._decode(value)
        query = Q(node__id=node_id)
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """Filter with value."""
        """Search with value."""
        query = Q()
        query |= Q(supply_chain__name__icontains=value)
        query |= Q(node__name__icontains=value)
        return queryset.filter(query)


class SupplyChainFilter(filters.FilterSet):
    """Filter for SupplyChain."""

    search = filters.CharFilter(method="search_fields")
    live_only = filters.BooleanFilter(method="filter_live_only")
    has_themes = filters.BooleanFilter(method="filter_has_themes")
    exclude_node = filters.CharFilter(method="exclude_node_supply_chain")

    class Meta:
        model = SupplyChain
        fields = ["search"]

    def search_fields(self, queryset, name, value):
        """Filter with value."""
        return queryset.filter(name__icontains=value)

    def filter_live_only(self, queryset, name, value):
        """Filter with value."""
        if value:
            current_node = self.request.parser_context["kwargs"]["node"]
            queryset = queryset.filter(
                supply_chain_connections__buyer=current_node
            )
        return queryset

    def filter_has_themes(self, queryset, name, value):
        """Filter with value."""
        if value:
            current_node = self.request.parser_context["kwargs"]["node"]
            queryset = queryset.filter(themes__node=current_node)
        return queryset

    def exclude_node_supply_chain(self, queryset, name, value):
        """To exclude selected node."""
        return queryset.exclude(nodesupplychain__node_id=decode(value))


class CompanyFilter(filters.FilterSet):
    """Filter for Company.

    filer by name and type
    """

    search = filters.CharFilter(method="search_fields")
    supply_chain = filters.CharFilter(method="filter_supply_chain")
    is_test = filters.CharFilter(method="filter_is_test")
    country = filters.CharFilter(method="filter_country")
    status = filters.NumberFilter()

    class Meta:
        model = Company
        fields = ["search", "supply_chain", "is_test", "country", "status"]

    def filter_is_test(self, queryset, name, value):
        """To perform function ilter_is_test."""
        if value == "true":
            query = Q(is_test=True)
        elif value == "false":
            query = Q(is_test=False)
        else:
            query = Q()
        return queryset.filter(query)

    def filter_supply_chain(self, queryset, name, value):
        """Filter with value."""
        sc_id = comm_lib._decode(value)
        query = Q(supply_chains__id=sc_id)
        return queryset.filter(query)

    def filter_primary_operation(self, queryset, name, value):
        """Filter with value."""
        op_id = comm_lib._decode(value)
        query = Q(primary_operation__id=op_id)
        return queryset.filter(query)

    def filter_country(self, queryset, name, value):
        """Filter with value."""
        query = Q(country__icontains=value)
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """Filter with value."""
        return queryset.filter(name__icontains=value)


class LabelFilter(filters.FilterSet):
    """Filter for SupplyChain."""

    name = filters.CharFilter(lookup_expr="icontains")
    supply_chain = filters.CharFilter(method="filter_supply_chain")
    used = filters.BooleanFilter(method="exclude_unused")
    used_in = filters.CharFilter(method="used_in_sc")

    class Meta:
        model = Label
        fields = ["name"]

    def filter_supply_chain(self, queryset, name, value):
        """Filter with value."""
        sc_id = comm_lib._decode(value)
        query = Q(supply_chains__id=sc_id)
        return queryset.filter(query)

    def exclude_unused(self, queryset, name, value):
        """Filter with value."""
        if value:
            queryset = queryset.exclude(connections=None)
        return queryset

    def used_in_sc(self, queryset, name, value):
        """Filter with value."""
        sc_id = comm_lib._decode(value)
        return queryset.filter(connections__supply_chain__id=sc_id)


class ConnectionNodeFilter(filters.FilterSet):
    """Filter for Connection Nodes."""

    type = filters.NumberFilter()
    search = filters.CharFilter(method="search_fields")
    claims = filters.CharFilter(method="filter_by_claims")
    name = filters.CharFilter(method="search_fields")
    country = filters.CharFilter(method="filter_by_country")
    province = filters.CharFilter(method="filter_by_province")
    location_type = filters.CharFilter(method="filter_by_location_type")
    connection = filters.CharFilter(method="filter_by_connection")

    class Meta:
        model = Node
        fields = [
            "type", "search", "name", "country", "province", 
            "location_type", "connection"
        ]

    def filter_by_claims(self, queryset, name, value):
        """Filter with value."""
        for val in value.split(","):
            claim_id = comm_lib._decode(val)
            queryset = queryset.filter(
                claims__claim__id=claim_id, claims__status=STATUS_APPROVED
            )
        return queryset

    def filter_by_name(self, queryset, name, value):
        """Filter with value."""
        query = Q(company__name__icontains=value)
        return queryset.filter(query)
    
    def filter_by_country(self, queryset, name, value):
        """Filter with value."""
        query = Q(farmer__country__iexact=value)
        return queryset.filter(query)

    def filter_by_province(self, queryset, name, value):
        """Filter with value."""
        query = Q(farmer__province__iexact=value)
        return queryset.filter(query)

    def filter_by_location_type(self, queryset, name, value):
        """Filter with value."""
        query = Q(farmer__plots__location_type__iexact=value)
        return queryset.filter(query)

    def filter_by_connection(self, queryset, name, value):
        """Filter with value."""
        operation_id = comm_lib._decode(value)
        query = Q(primary_operation__id=operation_id)
        return queryset.filter(query)
    
    @staticmethod
    def farmer_name_filter(value, conditions):
        """Filter based on the farmer's name (first and last)."""
        if ' ' in value:
            first_name, last_name = value.split(' ', 1)
            conditions.append(
                Q(farmer__first_name__icontains=first_name) & 
                Q(farmer__last_name__icontains=last_name)
            )
        else:
            conditions.append(
                Q(farmer__first_name__icontains=value) | 
                Q(farmer__last_name__icontains=value)
            )
        return

    def filter_common_fields(self, value, conditions, search_by):
        """Helper to filter common fields (email, address, etc.)."""
        common_fields = {
            'email': [
                ('farmer__email', 'company__email')
            ],
            'address': [
                ('farmer__street', 'company__street'),
                ('farmer__city', 'company__city'),
                ('farmer__sub_province', 'company__sub_province'),
                ('farmer__province', 'company__province'),
                ('farmer__country', 'company__country')
            ],
            'reference_number': [
                ('farmer__farmer_references__number', None)
            ]
        }

        if search_by in common_fields:
            for farmer_field, company_field in common_fields[search_by]:
                conditions.append(Q(**{f"{farmer_field}__icontains": value}))
                if company_field:  
                    conditions.append(
                        Q(**{f"{company_field}__icontains": value})
                    )

    def search_fields(self, queryset, name, value):
        """Filter with value based on search criteria."""
        search_by = self.request.query_params.get('search_by', None)
        node_type = self.request.query_params.get('type', '1')

        conditions = []

        # Determine the search criteria and build conditions accordingly
        if search_by == 'name':
            if node_type == "2":
                self.farmer_name_filter(value, conditions)
            else:
                conditions.append(Q(company__name__icontains=value))
        elif search_by in ['email', 'address', 'reference_number']:
            self.filter_common_fields(value, conditions, search_by)
        else:
            # Default search: Search across multiple fields
            conditions.append(Q(company__name__icontains=value))
            self.farmer_name_filter(value, conditions)
            self.filter_common_fields(value, conditions, 'email')
            self.filter_common_fields(value, conditions, 'address')
            self.filter_common_fields(value, conditions, 'reference_number')
        
        query = Q()
        for condition in conditions:
            query |= condition
        
        return queryset.filter(query)