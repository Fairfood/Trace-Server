from celery.result import AsyncResult
from common.library import decode
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from v2.accounts import permissions as user_permissions
from v2.reports.constants import COMPLETED
from v2.reports.constants import REVOKED
from v2.reports.models import Export
from v2.reports.serializers import ExportSerializer
from v2.supply_chains import permissions as sc_permissions


class ExportViewSet(ModelViewSet):
    """APIs for file exports."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )

    queryset = Export.objects.all()
    serializer_class = ExportSerializer
    allowed_methods = ("post", "get", "retrieve")

    def get_object(self):
        """Overridden function for updating pk value to decrypted value."""
        if "pk" in self.kwargs:
            self.kwargs["pk"] = decode(self.kwargs["pk"])
        return super().get_object()

    def get_queryset(self):
        """Overridden for exclude revoked in listing and retrieving."""
        queryset = super().get_queryset()
        if not self.request.method == "GET":
            return queryset
        return queryset.exclude_revoked().filter(node=self.kwargs["node"])

    def create(self, request, *args, **kwargs):
        """Overridden for injecting node idencode into request data."""
        node = self.kwargs.get("node", None)
        user = self.kwargs.get("user", None)
        request.data["node"] = node.idencode if node else None
        request.data["creator"] = user.idencode
        return super().create(request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def revoke(self, request, **kwargs):
        """To revoke the task of generating file if it is still happening."""
        instance = get_object_or_404(self.queryset, pk=decode(kwargs["pk"]))
        if instance.status != COMPLETED:
            AsyncResult(instance.task_id).revoke(terminate=True)
        instance.status = REVOKED
        instance.save(update_fields=["status"])
        return Response("Task revoked")
