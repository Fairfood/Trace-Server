"""Views related to tracing the batch in products app."""
from operator import methodcaller

from common import library as comm_lib
from common.cache import filesystem_cache
from common.library import unix_to_datetime
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import translation
from rest_framework import generics
from rest_framework.response import Response
from v2.accounts import permissions as user_permissions
from v2.dashboard.models import CITheme
from v2.products.models import Batch
from v2.products.serializers import trace as trace_serializers
from v2.products.serializers.trace_operational import (
    TraceClaimsWithBatchSerializer,
)
from v2.products.serializers.trace_operational import TraceMapSerializer
from v2.products.serializers.trace_operational import (
    TraceStagesWithBatchSerializer,
)
from v2.products.serializers.trace_operational import (
    TraceTransactionsWithBatchActorSerializer,
)
from v2.supply_chains.models import Node


class TraceBatch(generics.RetrieveAPIView):
    """API to get batch details."""

    permission_classes = (user_permissions.CIValidTOTP,)

    serializer_class = trace_serializers.TraceBatchSerializer

    queryset = Batch.objects.all()

    def retrieve(self, request, *args, **kwargs):
        """
        This code is for temporary fix (response cached) for CI data load time
        issue.
        Args:
            request:
            *args:
            **kwargs: {'pk':345678}

        Returns: Response()
        """
        key = f'ci_api_cache_{kwargs["pk"]}'
        cached_data = cache.get(key)

        if cached_data:
            data = cached_data
            return Response(data)
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        if kwargs["pk"] == 221719:
            cache.set(key, data, None)
        return Response(data)


class BaseTraceRetrieveAPIView(generics.RetrieveAPIView):
    """Class to handle BaseTraceRetrieveAPIView and functions."""

    permission_classes = (user_permissions.CIValidTOTP,)
    queryset = Batch.objects.all()
    param_object_methods = ["get_theme_object"]
    response_cache = False
    cache_prefix = ""
    language_cache = False

    def retrieve(self, request, *args, **kwargs):
        """To perform function retrieve."""
        instance = self.get_object()
        extra_objects = [
            methodcaller(fun)(self) for fun in self.param_object_methods
        ]
        if self.response_cache:
            data = self._cache_response(instance, *extra_objects)
            return Response(data)
        serializer = self.serializer_class(
            instance,
            *extra_objects,
            context={"request": self.request, "view": self},
        )
        return Response(serializer.data)

    def get_theme_object(self):
        """To perform function get_theme_object."""
        theme_name = self.request.query_params.get("theme", None)
        if not theme_name:
            raise ValidationError("theme is required")
        try:
            theme = CITheme.objects.get(name=theme_name)
        except CITheme.DoesNotExist:
            raise ValidationError("enter a valid theme")
        return theme

    def _cache_response(self, instance, *extra_objects):
        """To perform function _cache_response."""
        if not self.cache_prefix:
            self.cache_prefix = self.__class__.__name__
        key = "_".join(
            [
                self.cache_prefix,
                str(instance.id),
                *[str(obj.id) for obj in extra_objects],
            ]
        )
        key = self._clean_key(key)
        data = filesystem_cache.get(key)
        if data is not None:
            return data
        serializer = self.serializer_class(
            instance,
            *extra_objects,
            context={"request": self.request, "view": self},
        )
        data = serializer.data
        filesystem_cache.set(key, data)
        return data

    def _clean_key(self, key):
        """To perform function _clean_key."""
        if self.language_cache:
            current_language = translation.get_language()
            key = key + "_" + current_language
        return key


class TraceClaimWithBatch(BaseTraceRetrieveAPIView):
    """Class to handle TraceClaimWithBatch and functions."""

    serializer_class = TraceClaimsWithBatchSerializer
    response_cache = True
    cache_prefix = "claim"
    language_cache = True


class TraceMap(BaseTraceRetrieveAPIView):
    """Class to handle TraceMap and functions."""

    serializer_class = TraceMapSerializer
    response_cache = True
    cache_prefix = "map"
    language_cache = True


class TraceStagesWithBatch(BaseTraceRetrieveAPIView):
    """Class to handle TraceStagesWithBatch and functions."""

    serializer_class = TraceStagesWithBatchSerializer
    response_cache = True
    cache_prefix = "stage"
    language_cache = True


class TraceTransactionsWithBatchActor(BaseTraceRetrieveAPIView):
    """Class to handle TraceTransactionsWithBatchActor and functions."""

    serializer_class = TraceTransactionsWithBatchActorSerializer
    param_object_methods = [
        "get_theme_object",
        "get_actor_object",
        "get_paginate_index",
        "get_filters",
    ]

    def get_actor_object(self):
        """To perform function get_actor_object."""
        actor = self.request.query_params.get("actor", None)
        if not actor:
            raise ValidationError("actor is required")
        try:
            node = Node.objects.get(pk=comm_lib.decode(actor))
        except Node.DoesNotExist:
            raise ValidationError("enter a valid actor")
        return node

    def get_paginate_index(self):
        """To pass limit offset to the serializer to get a paginated
        transaction list."""

        # setting default limit as 20 to avoid conflict in storytelling
        limit = self.request.query_params.get("limit", 20)
        offset = self.request.query_params.get("offset", 0)
        return limit, offset

    def get_filters(self):
        """To filter with query params for transaction report."""
        query = {}
        product = self.request.query_params.get("product_name", None)
        date = self.request.query_params.get("date", None)
        _type = self.request.query_params.get("type", None)
        search = self.request.query_params.get("search", None)

        if product:
            query["result_batches__product__name"] = product
        if date:
            dt = unix_to_datetime(date).date()
            query["date__date"] = dt
        if _type:
            query["type"] = _type
        if search:
            query["search"] = search
        return query
