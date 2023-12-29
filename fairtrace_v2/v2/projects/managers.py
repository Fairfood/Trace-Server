from common.library import decode
from common.library import unix_to_datetime
from django.apps import apps
from django.db import models
from django.db.models import Q


class PaymentQuerySet(models.QuerySet):
    """QuerySet for filtering and manipulating Payment objects.

    This QuerySet provides methods for filtering and manipulating
    Payment objects based on various criteria. It allows filtering
    premiums based on node IDs, the updated date, and other query
    parameters.
    """

    def filter_by_query_params(self, request):
        """Filter with request params."""
        data = request.query_params.copy()
        data["node"] = request.parser_context["kwargs"]["node"]
        return self.filter_by_data(data)

    def filter_by_data(self, data):
        """Filter with data params."""
        qs = self
        search = data.get("search")
        payment_type = data.get("payment_type")
        updated_after = data.get("updated_after")
        farmer = data.get("farmer")

        if search:
            qs = qs.filter(description__icontains=search)

        if not farmer:
            node = data.get("node")
        else:
            node_model = apps.get_model("supply_chains", "Node")
            node = node_model.objects.get(pk=decode(farmer))
        qs = qs.filter_by_current_node(node)

        if payment_type:
            qs = qs.filter(payment_type=payment_type)
        if updated_after:
            qs = qs.filter_by_updated_after(updated_after)
        return qs

    def filter_by_current_node(self, node):
        """Filter premium with node."""
        return self.filter(Q(source=node) | Q(destination=node))

    def filter_by_updated_after(self, update_after):
        """Return data only after this date."""
        dt = unix_to_datetime(update_after)
        return self.filter(created_on__gt=dt)


class ProjectPremiumQuerySet(models.QuerySet):
    """QuerySet for filtering and manipulating ProjectPremium objects.

    This QuerySet provides methods for filtering and manipulating
    ProjectPremium objects based on various criteria. It allows
    filtering premiums based on node IDs, the updated date, and other
    query parameters.
    """

    def filter_by_query_params(self, request):
        """Filter with request params."""
        qs = self

        # Get node from request
        try:
            node = request.parser_context["kwargs"]["node"]
        except KeyError:
            node = None

        # get all buyers of the mode to get buyer premium.
        if node:
            node_ids = list(node.get_buyers().values_list("id", flat=True))
            node_ids += [node.id]
            qs = qs.filter_by_node_ids(node_ids)
        else:
            qs = qs.none()

        updated_after = request.query_params.get("updated_after")
        if updated_after:
            qs = qs.filter_by_updated_after(updated_after)
        return qs

    def filter_by_node_ids(self, node_ids):
        """Filter premium with node."""
        return self.filter(owner_id__in=node_ids)

    def filter_by_updated_after(self, update_after):
        """Return data only after this date."""
        dt = unix_to_datetime(update_after)
        return self.filter(updated_on__gt=dt)
