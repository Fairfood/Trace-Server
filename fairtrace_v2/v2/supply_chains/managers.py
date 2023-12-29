from datetime import datetime

from django.apps import apps

from common.library import decode
from django.conf import settings
from django.db import models
from django.db.models import Count, Case, When, CharField, Subquery, F
from django.db.models import Q
from django.db.models import Value
from django.db.models.functions import Trunc, Concat
from pytz import timezone
from v2.supply_chains.constants import NODE_STATUS_ACTIVE, NODE_TYPE_FARM, \
    NODE_TYPE_COMPANY, CONNECTION_STATUS_VERIFIED


class NodeQuerySet(models.QuerySet):
    """NodeQuerySet is an additional layer to handle queryset level
    functionalities."""

    def sort_by_query_params(self, request):
        """Enable sorting."""
        queryset = self
        sort_by = request.query_params.get("sort_by", None)
        order_by = request.query_params.get("order_by", "asc")
        field_set = (
            "country",
            "status",
            "company.name",
            "created_on",
            "farmer.first_name",
        )
        if sort_by:
            sort_by = sort_by.strip()
            if sort_by in field_set:
                sort_by = self._clean_field(sort_by)
                if order_by.lower().strip() == "desc":
                    sort_by = f"-{sort_by}"
                return queryset.order_by(sort_by)
        return queryset

    def filter_queryset(self, request):
        """filters queryset with different request parameters."""
        queryset = self

        _type = request.query_params.get("type", None)
        start_date = request.query_params.get("start_date", None)
        end_date = request.query_params.get("end_date", None)
        supply_chain = request.query_params.get("supply_chain", None)
        product = request.query_params.get("product", None)
        _status = request.query_params.get("status", None)
        primary_operation = request.query_params.get("primary_operation", None)
        search = request.query_params.get("search", None)

        if _type:
            queryset = queryset.filter(type=_type)
        if _status:
            node = request.parser_context["kwargs"]["node"]
            queryset = queryset.filter_with_status(_status, node)

        if start_date:
            queryset = queryset.filter(
                created_on__gt=self.convert_timezone(start_date)
            )
        if end_date:
            queryset = queryset.filter(
                created_on__lte=self.convert_timezone(end_date)
            )
        if supply_chain:
            queryset = queryset.filter(
                supply_chains__id=decode(supply_chain),
                supply_chains__active=True,
            )
        if primary_operation:
            if supply_chain:
                queryset = queryset.filter(
                    nodesupplychain__supply_chain_id=decode(supply_chain),
                    nodesupplychain__primary_operation_id=decode(
                        primary_operation
                    ),
                ).distinct()

            else:
                queryset = queryset.filter(
                    primary_operation_id=decode(primary_operation)
                )

        if product:
            product_id = decode(product)
            out_source_batches = Q(
                outgoing_transactions__source_batches__product__id=product_id
            )
            out_result_batches = Q(
                outgoing_transactions__result_batches__product__id=product_id
            )
            in_source_batches = Q(
                incoming_transactions__source_batches__product__id=product_id
            )
            in_result_batches = Q(
                incoming_transactions__result_batches__product__id=product_id
            )
            queryset = queryset.filter(
                Q(
                    out_source_batches
                    | out_result_batches
                    | in_source_batches
                    | in_result_batches
                )
            ).distinct()

        if search:
            queryset = self.filter(pk__in=queryset.values("id"))
            queryset = queryset.annotate(full_name_search=Case(
                When(
                    type=NODE_TYPE_FARM,
                    then=Concat(
                        "farmer__first_name",
                        Value(" "),
                        "farmer__last_name",
                    ),
                ),
                When(
                    type=NODE_TYPE_COMPANY,
                    then="company__name",
                ),
                default=Value(""),
                output_field=CharField(),
            )).filter(full_name_search__icontains=search)

        return queryset

    @staticmethod
    def convert_timezone(date):
        """To perform function convert_timezone."""
        local_tz = timezone(settings.TIME_ZONE)
        date = datetime.strptime(date, "%Y-%m-%d")
        return local_tz.localize(date)

    def filter_with_status(self, status, node):
        """Filtering queryset with status."""
        connection_model = apps.get_model("supply_chains", "Connection")
        invitation_subquery = connection_model.objects.filter(
            invitation__invitee_id=models.OuterRef("pk"),
            invitation__inviter=node
        )

        # Verified status cannot be taken from Node model directly.
        queryset = self.annotate(
            verfied_status=F('status'),
            email_invite=Subquery(
                invitation_subquery.values("invitation__email_sent")[:1]),
            connection_status=Case(
                When(verfied_status=NODE_STATUS_ACTIVE,
                     then=Value("1")),
                When(email_invite=True, then=Value("2")),
                output_field=CharField(),
                default=Value("3"),
            ))
        return queryset.filter(connection_status=status)

    def group_by_with_country(self, extra_fields=()):
        """Grouping queryset with country and extra_fields.

        * extra_fields -> Should be direct fields and the count will be
                effected by these fields.

         *   [
                    {
                        "country": "Afghanistan",
                        "type": 1,
                        "count": 630
                    },
                    {
                        "country": "Afghanistan",
                        "type": 2,
                        "count": 290
                    }
                ]
        """
        queryset = (
            self.values("country", *extra_fields)
            .annotate(count=Count("country"))
            .order_by("country")
        )
        return queryset

    def exclude_test(self):
        """Exclude test nodes."""
        return self.filter(is_test=False)

    def group_count_with_created_on(self, trunc_type="month", extra_fields=()):
        """Grouping queryset with created_on and extra_fields.

        * extra_fields -> Should be direct fields and the count will be
                effected by these fields.
        * trunc_type -> Options month/week/day/quarter/year
        """
        queryset = self.annotate(
            truncated_by=Value(trunc_type, output_field=models.CharField()),
            grouped_by=Trunc("created_on", kind=trunc_type),
        )
        return (
            queryset.values("truncated_by", "grouped_by", *extra_fields)
            .annotate(count=Count("grouped_by"))
            .order_by("grouped_by")
        )

    @staticmethod
    def _clean_field(sort_by):
        if "." in sort_by:
            sort_by = sort_by.replace(".", "__")
        return sort_by

    def only_active(self):
        """Returns only active Nodes."""
        return self.filter(status=NODE_STATUS_ACTIVE)

    def only_pending(self):
        """Returns only non-active Nodes."""
        return self.exclude(status=NODE_STATUS_ACTIVE)


class NodeSupplyChainQuerySet(models.QuerySet):
    """NodeSupplyChainQuerySet is an additional layer to handle queryset level
    functionalities."""

    def filter_queryset(self, request):
        """filters queryset with different request parameters."""
        queryset = self

        supply_chain = request.query_params.get("supply_chain", None)

        if supply_chain:
            queryset = queryset.filter(supply_chain=decode(supply_chain))
        return queryset

    def exclude_test(self):
        """exclude test nodes."""
        return self.filter(node__is_test=False)


class ReferenceQuerySet(models.QuerySet):
    """ReferenceQuerySet is an additional layer to handle queryset level
    functionalities."""

    def filter_by_query_params(self, request):
        """filters queryset with different request parameters."""
        queryset = self

        search = request.query_params.get("search", None)

        if search:
            queryset = queryset.filter(name__icontains=search)
        # show only editable references
        queryset = queryset.filter(is_editable=True)
        return queryset


class FarmerReferenceQuerySet(models.QuerySet):
    """FarmerReferenceQuerySet is an additional layer to handle queryset level
    functionalities."""

    def filter_by_query_params(self, request):
        """filters queryset with different request parameters."""
        queryset = self

        search = request.query_params.get("search", None)
        farmer = request.query_params.get("farmer", None)
        source = request.query_params.get("source", None)

        if search:
            queryset = queryset.filter(
                Q(reference__name__icontains=search)
                | Q(farmer__first_name__icontains=search)
                | Q(farmer__last_name__icontains=search)
                | Q(number__icontains=search)
            )
        if farmer:
            farmer_id = decode(farmer)
            queryset = queryset.filter(farmer_id=farmer_id)
        if source:
            source_id = decode(source)
            queryset = queryset.filter(source_id=source_id)
        return queryset


class FarmerPlotQuerySet(models.QuerySet):
    """FarmerPlotQuerySet is an additional layer to handle queryset level
    functionalities."""

    def filter_by_query_params(self, request):
        """filters queryset with different request parameters."""
        queryset = self

        farmer = request.query_params.get("farmer", None)

        if farmer:
            farmer_id = decode(farmer)
            queryset = queryset.filter(farmer_id=farmer_id)
        return queryset


class FarmerAttachmentQuerySet(models.QuerySet):
    """FarmerPlotQuerySet is an additional layer to handle queryset level
    functionalities."""

    def filter_by_query_params(self, request):
        """filter with request params."""
        queryset = self
        farmer = request.query_params.get("farmer")
        if farmer:
            farmer_id = decode(farmer)
            queryset = queryset.filter(farmer_id=farmer_id)
        return queryset
