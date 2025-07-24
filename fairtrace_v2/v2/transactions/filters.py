"""Filters used in the app transactions."""
from common import library as comm_lib
from django.db.models import Q
from django.utils.timezone import datetime
from django_filters import rest_framework as filters
from v2.products.constants import PRODUCT_TYPE_CARBON
from v2.transactions import constants
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import InternalTransaction


class ExternalTransactionFilter(filters.FilterSet):
    """Filter for External Transactions.

    Over-ridden to accommodate product
    """

    def __init__(self, node=None, **kwargs):
        """To perform function __init__."""
        super().__init__(**kwargs)
        self.node = node
        if "archived" not in self.data:
            if hasattr(self.data, "_mutable"):
                self.data._mutable = True
                self.data["archived"] = "false"
                self.data._mutable = False
            else:
                self.data["archived"] = "false"

    type = filters.NumberFilter(method="filter_type")
    creator = filters.CharFilter(method="filter_creator")
    product = filters.CharFilter(method="filter_product")
    node = filters.CharFilter(method="filter_node")
    supply_chain = filters.CharFilter(method="filter_supply_chain")
    search = filters.CharFilter(method="search_fields")
    date_from = filters.CharFilter(method="filter_date_from")
    date_to = filters.CharFilter(method="filter_date_to")
    date_on = filters.CharFilter(method="filter_date_on")
    quantity_from = filters.NumberFilter(method="filter_quantity_from")
    quantity_to = filters.NumberFilter(method="filter_quantity_to")
    quantity_is = filters.CharFilter(method="filter_quantity_is")
    is_carbon_product = filters.BooleanFilter(method="filter_carbon_product")

    class Meta:
        model = ExternalTransaction
        fields = ["type", "product", "archived", "is_carbon_product"]   

    def get_node(self):
        """Returns the node if available."""
        return (
            self.node
            if self.node
            else self.request.parser_context["kwargs"]["node"]
        )

    def filter_type(self, queryset, name, value):
        """Filter with value."""
        current_node = self.get_node()
        if value == constants.EXTERNAL_TRANS_TYPE_REVERSAL:
            queryset = queryset.filter(type=value)
        elif value == constants.EXTERNAL_TRANS_TYPE_INCOMING:
            queryset = queryset.filter(
                destination__id=current_node.id
            ).exclude(type=constants.EXTERNAL_TRANS_TYPE_REVERSAL)
        else:
            queryset = queryset.filter(source__id=current_node.id).exclude(
                type=constants.EXTERNAL_TRANS_TYPE_REVERSAL
            )
        return queryset

    def filter_product(self, queryset, name, value):
        """Filter with value."""
        product_id = comm_lib._decode(value)
        query = Q(source_batches__product__id=product_id) | Q(
            result_batches__product__id=product_id
        )
        return queryset.filter(query)
    
    def filter_carbon_product(self, queryset, name, value):
        """
        Filter transactions by carbon-related products.
        If `value` is True, return only transactions involving carbon products.
        If `value` is False, exclude them.
        """
        query = (
            Q(source_batches__product__type=PRODUCT_TYPE_CARBON) |
            Q(result_batches__product__type=PRODUCT_TYPE_CARBON)
        )
        if not value:
            query = ~query
        return queryset.filter(query)

    def filter_node(self, queryset, name, value):
        """Filter with value."""
        node_id = comm_lib._decode(value)
        query = Q(source__id=node_id) | Q(destination__id=node_id)
        return queryset.filter(query)

    def filter_supply_chain(self, queryset, name, value):
        """Filter with value."""
        sc_id = comm_lib._decode(value)
        query = Q(source_batches__product__supply_chain__id=sc_id) | Q(
            result_batches__product__supply_chain__id=sc_id
        )
        return queryset.filter(query)

    def search_fields(self, queryset, name, value):
        """Search with value."""
        query = Q()
        query |= Q(number__icontains=value)
        query |= Q(source_batches__product__name__icontains=value)
        query |= Q(result_batches__product__name__icontains=value)
        query |= Q(source__company__name__icontains=value)
        query |= Q(source__farmer__first_name__icontains=value)
        query |= Q(source__farmer__last_name__icontains=value)
        return queryset.filter(query)

    def filter_date_from(self, queryset, name, value):
        """Filter with value."""
        value += "-00:00:00"
        value = datetime.strptime(value, "%d/%m/%Y-%H:%M:%S")
        query = Q(date__gte=value)
        return queryset.filter(query)

    def filter_date_to(self, queryset, name, value):
        """Filter with value."""
        value += "-23:59:59"
        value = datetime.strptime(value, "%d/%m/%Y-%H:%M:%S")
        query = Q(date__lte=value)
        return queryset.filter(query)

    def filter_date_on(self, queryset, name, value):
        """Filter with value."""
        value_from = value + "-00:00:00"
        value_from = datetime.strptime(value_from, "%d/%m/%Y-%H:%M:%S")
        value_to = value + "-23:59:59"
        value_to = datetime.strptime(value_to, "%d/%m/%Y-%H:%M:%S")
        query = Q(date__gte=value_from) & Q(date__lte=value_to)
        return queryset.filter(query)

    def filter_quantity_is(self, queryset, name, value):
        """Filter with value."""
        current_node = self.get_node()
        query = Q(source=current_node, _source_quantity=value) | Q(
            destination=current_node, _destination_quantity=value
        )
        return queryset.filter(query)

    def filter_quantity_from(self, queryset, name, value):
        """To perform function ilter_quantity_from."""
        current_node = self.get_node()
        query = Q(source=current_node, _source_quantity__gte=value) | Q(
            destination=current_node, _destination_quantity__gte=value
        )
        return queryset.filter(query)

    def filter_quantity_to(self, queryset, name, value):
        """To perform function ilter_quantity_to."""
        current_node = self.get_node()
        query = Q(source=current_node, _source_quantity__lte=value) | Q(
            destination=current_node, _destination_quantity__lte=value
        )
        return queryset.filter(query)

    def filter_creator(self, queryset, name, value):
        """To perform function filter_creator."""
        creator_id = comm_lib._decode(value)
        return queryset.filter(creator_id=creator_id)


class InternalTransactionFilter(filters.FilterSet):
    """Filter for External Transactions.

    Over-ridden to accommodate product
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

    type = filters.NumberFilter()
    supply_chain = filters.CharFilter(method="filter_supply_chain")
    search = filters.CharFilter(method="search_fields")
    date_from = filters.CharFilter(method="filter_date_from")
    date_to = filters.CharFilter(method="filter_date_to")
    date_on = filters.CharFilter(method="filter_date_on")
    creator = filters.CharFilter(method="filter_creator")
    quantity_from = filters.NumberFilter(
        field_name="_source_quantity", lookup_expr="gte"
    )
    quantity_to = filters.NumberFilter(
        field_name="_source_quantity", lookup_expr="lte"
    )
    source_product = filters.CharFilter(method="filter_source_product")
    destination_product = filters.CharFilter(
        method="filter_destination_product"
    )
    quantity_is = filters.CharFilter(method="filter_quantity_is")
    is_carbon_product = filters.BooleanFilter(method="filter_carbon_product")

    class Meta:
        model = InternalTransaction
        fields = ["type", "supply_chain", "archived", "is_carbon_product"]

    def filter_supply_chain(self, queryset, name, value):
        """Filter with value."""
        sc_id = comm_lib._decode(value)
        query = Q(source_batches__product__supply_chain__id=sc_id) | Q(
            result_batches__product__supply_chain__id=sc_id
        )
        return queryset.filter(query).order_by().distinct("id").order_by("-id")

    def search_fields(self, queryset, name, value):
        """Search with value."""
        query = Q()
        query |= Q(number__icontains=value)
        query |= Q(source_batches__product__name__icontains=value)
        query |= Q(result_batches__product__name__icontains=value)
        return queryset.filter(query)

    def filter_date_from(self, queryset, name, value):
        """Filter with value."""
        value += "-00:00:00"
        value = datetime.strptime(value, "%d/%m/%Y-%H:%M:%S")
        query = Q(date__gte=value)
        return queryset.filter(query)

    def filter_date_to(self, queryset, name, value):
        """Filter with value."""
        value += "-23:59:59"
        value = datetime.strptime(value, "%d/%m/%Y-%H:%M:%S")
        query = Q(date__lte=value)
        return queryset.filter(query)

    def filter_date_on(self, queryset, name, value):
        """Filter with value."""
        value_from = value + "-00:00:00"
        value_from = datetime.strptime(value_from, "%d/%m/%Y-%H:%M:%S")
        value_to = value + "-23:59:59"
        value_to = datetime.strptime(value_to, "%d/%m/%Y-%H:%M:%S")
        query = Q(date__gte=value_from) & Q(date__lte=value_to)
        return queryset.filter(query)

    def filter_source_product(self, queryset, name, value):
        """Filter with value."""
        product_id = comm_lib._decode(value)
        query = Q(source_batches__product__id=product_id)
        return queryset.filter(query).order_by().distinct("id").order_by("-id")

    def filter_destination_product(self, queryset, name, value):
        """Filter with value."""
        product_id = comm_lib._decode(value)
        query = Q(result_batches__product__id=product_id)
        return queryset.filter(query).order_by().distinct("id").order_by("-id")

    def filter_quantity_is(self, queryset, name, value):
        """Filter with value."""
        query = Q(_source_quantity=value)
        return queryset.filter(query)

    def filter_creator(self, queryset, name, value):
        """Filter with value."""
        creator_id = comm_lib._decode(value)
        query = Q(creator_id=creator_id)
        return queryset.filter(query)

    def filter_carbon_product(self, queryset, name, value):
        """
        Filter transactions by carbon-related products.
        If `value` is True, return only transactions involving carbon products.
        If `value` is False, exclude them.
        """
        query = (
            Q(source_batches__product__type=PRODUCT_TYPE_CARBON) |
            Q(result_batches__product__type=PRODUCT_TYPE_CARBON)
        )
        if not value:
            query = ~query
        return queryset.filter(query)


class TransactionAttachmentFilter(filters.FilterSet):
    """
    FilterSet for filtering transaction attachments.

    ...

    Attributes
    ----------
    transaction : CharFilter
        Filter for filtering attachments by transaction ID.

    """

    transaction = filters.CharFilter(method="filter_with_transaction")

    class Meta:
        fields = ["transaction"]

    @staticmethod
    def filter_with_transaction(queryset, name, value):
        """Custom filter method for filtering attachments by transaction ID.

        Parameters:
        - queryset (QuerySet): The initial queryset to filter.
        - name (str): The name of the filter field.
        - value (str): The value of the filter field.

        Returns:
        QuerySet: The filtered queryset.
        """
        transaction_id = comm_lib.decode(value)
        return queryset.filter(transaction_id=transaction_id)
