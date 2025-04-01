import json

from common.drf_custom.views import IdencodeObjectViewSetMixin
from common.library import success_response
from rest_framework import viewsets
from v2.accounts.permissions import IsAuthenticated
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.filters import CompanyFilter
from v2.supply_chains.filters import FarmerFilter
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Node
from v2.supply_chains.permissions import IsFairfoodAdmin
from v2.supply_chains.serializers.admin_dashboard_v3 import (
    AdminCompanyModelSerializer,
)
from v2.supply_chains.serializers.admin_dashboard_v3 import (
    AdminFarmerModelSerializer,
)


class CountryNodeCountViewSet(viewsets.ViewSet):
    """API to count farmer and company against each country available."""

    permission_classes = (IsAuthenticated, IsFairfoodAdmin)
    queryset = Node.objects.all()

    def list(self, request, *args, **kwargs):
        """Returns the grouped Nodes with count."""
        data = []
        queryset = self.queryset.filter_queryset(request).exclude_test()
        if queryset:
            data = queryset.group_by_with_country(extra_fields=("type",))
        return success_response(
            data=self._combine_node_count_with_country(data)
        )

    def _combine_node_count_with_country(self, data):
        """Returns data in the following format.

        *   [
                {
                    "country": "Afghanistan",
                    "farmer_count": 5695,
                    "company_count": 630
                },
                {
                    "country": "Albania",
                    "farmer_count": 343,
                    "company_count": 290
                }
            ]
        """
        unique_country_data = {}
        country_info = self._load_country_lat_long()
        for country_stat in data:
            if country_stat["country"] not in unique_country_data:
                unique_country_data[country_stat["country"]] = {
                    "country": country_stat["country"],
                    "country_code": country_info[country_stat["country"]][
                        "alpha_2"
                    ],
                    "farmer_count": 0,
                    "company_count": 0,
                    "lat_long": country_info[country_stat["country"]][
                        "latlong"
                    ],
                    "count": 0,
                }
            value_dict = {"farmer_count": country_stat["count"]}
            if country_stat["type"] != NODE_TYPE_FARM:
                value_dict = {"company_count": country_stat["count"]}
            unique_country_data[country_stat["country"]].update(value_dict)
            self._add_total_count(unique_country_data[country_stat["country"]])
        return unique_country_data.values()

    @staticmethod
    def _load_country_lat_long():
        """To perform function _load_country_lat_long."""
        country_file = open("common/country_data/country_data.json")
        return json.load(country_file)

    @staticmethod
    def _add_total_count(data):
        """To perform function _add_total_count."""
        data["count"] = data["farmer_count"] + data["company_count"]


class AdminFarmerViewSet(
    IdencodeObjectViewSetMixin, viewsets.ReadOnlyModelViewSet
):
    """API to list all farmers in the system."""

    permission_classes = (IsAuthenticated, IsFairfoodAdmin)
    queryset = Farmer.objects.all().exclude_test()
    filterset_class = FarmerFilter
    serializer_class = AdminFarmerModelSerializer

    def get_queryset(self):
        """Adding extra qs functions."""
        return super().get_queryset().sort_by_query_params(self.request)


class AdminCompanyViewSet(viewsets.ReadOnlyModelViewSet):
    """API to list all Companies in the system."""

    permission_classes = (IsAuthenticated, IsFairfoodAdmin)
    queryset = Company.objects.all()
    filterset_class = CompanyFilter
    serializer_class = AdminCompanyModelSerializer

    def get_queryset(self):
        """Adding extra qs functions."""
        return super().get_queryset().sort_by_query_params(self.request)


class AdminNodeCountViewSet(viewsets.ViewSet):
    """API to count farmer and company against each joined date available."""

    permission_classes = (IsAuthenticated, IsFairfoodAdmin)
    queryset = Node.objects.all()

    def list(self, request, *args, **kwargs):
        """Returns the grouped Node with count."""
        queryset = self.queryset.filter_queryset(request).exclude_test()
        trunc_type = request.query_params.get("trunc_type", None)
        if not trunc_type:
            data = queryset.group_count_with_created_on(extra_fields=("type",))
        else:
            data = queryset.group_count_with_created_on(
                trunc_type, extra_fields=("type",)
            )
        return success_response(self._combine_node_count_with_created_on(data))

    @staticmethod
    def _combine_node_count_with_created_on(data):
        """Returns data in the following format.

        *   [
                {
                    "grouped_by": "2020-01-01T00:00:00+05:30",
                    "truncated_by": "month",
                    "farmer_count": 19,
                    "company_count": 94,
                    "count": 113,
                },
                {
                    "grouped_by": "2020-02-01T00:00:00+05:30",
                    "truncated_by": "month",
                    "farmer_count": 39,
                    "company_count": 18,
                    "count": 57,

                }
                        ]
        """
        unique_country_data = {}
        for i in data:
            if i["grouped_by"] not in unique_country_data:
                unique_country_data[i["grouped_by"]] = {
                    "grouped_by": i["grouped_by"],
                    "truncated_by": i["truncated_by"],
                    "farmer_count": 0,
                    "company_count": 0,
                }
            value_dict = {"farmer_count": i["count"]}
            if i["type"] != NODE_TYPE_FARM:
                value_dict = {"company_count": i["count"]}

            unique_country_data[i["grouped_by"]].update(value_dict)
        return unique_country_data.values()
