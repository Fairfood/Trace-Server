from django.db import models
from django.db.models import Q

from v2.bulk_uploads.constants import TEMPLATE_VISIBILITY_HIDDEN, \
    TEMPLATE_VISIBILITY_PUBLIC


class DataSheetTemplateQuerySet(models.QuerySet):
    """Data sheet template queryset."""

    def filter_by_query_params(self, request):
        """Filter the queryset based on the query params."""

        qs = self

        # Get the node from the request
        try:
            node = request.parser_context["kwargs"]["node"]
        except KeyError:
            node = None

        is_active = request.query_params.get("is_active")
        _type = request.query_params.get("type")
        search = request.query_params.get("search")
        visibility = request.query_params.get("visibility")

        qs = qs.filter_by_visibility(visibility)
        qs = qs.filter_by_undeleted()
        qs = qs.filter_by_current_node(node)
        qs = qs.filter_is_active(is_active)
        qs = qs.filter_type(_type)
        qs = qs.filter_by_search(search)
        return qs

    def filter_by_current_node(self, node):
        """Return the templates linked to the node."""
        return self.filter(
            Q(map_nodes__node=node) |
            Q(visibility=TEMPLATE_VISIBILITY_PUBLIC))

    def filter_type(self, _type):
        """Return the templates of the given type."""
        if _type is None:
            return self
        return self.filter(type=_type)

    def filter_by_search(self, search):
        """Return the templates of the given search."""
        if search is None:
            return self
        return self.filter(name__icontains=search)

    def filter_by_undeleted(self):
        """Return the templates that are not deleted."""
        return self.filter(is_deleted=False)

    def filter_is_active(self, flag):
        """Return the templates that are active."""
        if flag == 'true':
            return self.filter(is_active=True)
        elif flag == 'false':
            return self.filter(is_active=False)
        else:
            return self

    def filter_by_visibility(self, visibility):
        """Return the templates that are visible."""
        if visibility == "all":
            return self
        return self.exclude(visibility=TEMPLATE_VISIBILITY_HIDDEN)
