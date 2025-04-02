from common.library import decode
from django.db import models

# Managers to add more functionalities to Model.objects


class BatchQuerySet(models.QuerySet):
    """Class to handle BatchQuerySet and functions."""

    def sort_by_query_params(self, request):
        """To perform function sort_by_query_params."""
        queryset = self
        sort_by = request.query_params.get("sort_by", None)
        order_by = request.query_params.get("order_by", "asc")
        field_set = (
            "number",
            "product.name",
            "created_on",
            "current_quantity",
            "initial_quantity",
            "supplier.name",
        )
        if sort_by:
            sort_by = sort_by.strip()
            if sort_by in field_set:
                sort_by = self._clean_field(sort_by)
                if order_by.lower().strip() == "desc":
                    sort_by = f"-{sort_by}"
                return queryset.order_by(sort_by)
        return queryset

    @staticmethod
    def _clean_field(sort_by):
        """To perform function _clean_field."""
        if "." in sort_by:
            sort_by = sort_by.replace(".", "__")
            if sort_by.split("__")[0] == "supplier":
                sort_by = sort_by.replace(
                    "supplier", "source_transaction__supplier"
                )
        return sort_by
    
    def parents(self):
        """Returns parents"""
        queryset = self.model.objects.none()
        for item in self:
            queryset |= item.parents.all()
        return queryset



class ProductQuerySet(models.QuerySet):
    """Class to handle ProductQuerySet and functions."""

    def filter_queryset(self, request):
        """To perform function ilter_queryset."""
        queryset = self

        supply_chain = request.query_params.get("supply_chain", None)

        if supply_chain:
            supply_chain_id = decode(supply_chain)
            queryset = queryset.filter(supply_chain_id=supply_chain_id)
        return queryset


class BatchFarmerMappingQuerySet(models.QuerySet):
    """Custom queryset for BatchFarmerMapping model.

    This custom queryset provides additional methods for filtering and
    manipulating BatchFarmerMapping instances.
    """

    def filter_queryset(self, request):
        """Apply additional filters to the queryset.

        Parameters:
        - request: The request object.

        Returns:
        - QuerySet: The filtered queryset.
        """
        queryset = self
        return queryset

    def get_farmers(self, batch):
        """Get the farmers queryset for a specific batch.

        Parameters:
        - batch: The batch object.

        Returns:
        - QuerySet: The queryset of farmers related to the specified batch.
        """
        farmer_ids = list(self.filter(batch=batch).values_list(
            "farmer_id", flat=True
        ))
        return self.model.farmer.get_queryset().filter(pk__in=farmer_ids)

    def copy_farmers(self, batch, new_batch):
        """Copy farmers from one batch to another.

        This method creates new BatchFarmerMapping instances for the specified
        new batch, copying the farmers from the original batch.

        Parameters:
        - batch: The original batch object.
        - new_batch: The new batch object.
        """
        create_list = []
        for farmer in self.get_farmers(batch):
            create_list.append(self.model(batch=new_batch, farmer=farmer))
        self.model.objects.bulk_create(create_list, ignore_conflicts=True)
