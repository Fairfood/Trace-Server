"""View for bulk template."""
from common import library as comm_lib
from common.drf_custom import views as cust_view
from common.exceptions import BadRequest
from rest_framework import generics
from rest_framework.decorators import action
from v2.accounts import permissions as user_permissions
from v2.bulk_templates import models as temp_models
from v2.bulk_templates import permissions as bulk_permissions
from v2.bulk_templates.dynamic_bulk_upload.txn_sheet import (
    DynamicExcelProcessor,
)
from v2.bulk_templates.filters import TemplateFilter
from v2.bulk_templates.serializers import templates as temp_ser
from v2.supply_chains import permissions as sc_permissions


class TemplateViewSet(cust_view.IddecodeModelViewSet):
    """A simple ViewSet for viewing and editing the custom template of node."""

    serializer_class = temp_ser.TemplateSerializer
    filterset_class = TemplateFilter

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )

    def get_permissions(self):
        """To perform function get_permissions."""
        if self.request.method == "POST":
            self.permission_classes += (sc_permissions.HasNodeWriteAccess,)
        elif self.request.method == "PATCH":
            self.permission_classes += (
                sc_permissions.HasNodeWriteAccess,
                bulk_permissions.HasTemplateAccess,
            )
        return super(TemplateViewSet, self).get_permissions()

    def get_queryset(self):
        """To perform function get_queryset."""
        if self.request.method == "PATCH":
            return self.get_object()
        else:
            query = temp_models.Template.node_template_qs(self.kwargs["node"])
        return temp_models.Template.objects.filter(query)

    def list(self, request, *args, **kwargs):
        """Overriding response to add total count of templates."""
        response = super().list(request, args, kwargs)
        query = temp_models.Template.node_template_qs(self.kwargs["node"])
        response.data["total_count"] = temp_models.Template.objects.filter(
            query
        ).count()
        return response

    @action(
        methods=["post"],
        detail=False,
        permission_classes=[
            user_permissions.IsAuthenticated,
            sc_permissions.HasNodeAccess,
        ],
    )
    def verify(self, request, **kwargs):
        """Funtion for verify the excel data."""
        serializer = temp_ser.VerifyTemplateSerializer(
            data=request.data, context=kwargs
        )
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)
        serializer.save()
        return comm_lib._success_response(serializer.data)
        # return super(TemplateViewSet, self).verify(request, kwargs)

    @action(methods=["post"], detail=False, url_path="validate-name")
    def validate_name(self, request, **kwargs):
        """Funtion for validate the template name."""
        request.data["node"] = self.kwargs["node"].idencode
        serializer = temp_ser.ValidateTemplateNameSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequest(serializer.errors)

        return comm_lib._success_response(serializer.data)

    @action(
        methods=["get"],
        detail=True,
        permission_classes=[
            user_permissions.IsAuthenticated,
            sc_permissions.HasNodeAccess,
        ],
    )
    def preview(self, request, **kwargs):
        """Function for get details of data from excel."""
        processor = DynamicExcelProcessor(self.get_object())
        excel_data = processor.get_preview()
        return comm_lib._success_response(
            {"excel_data": list(excel_data)}, "Authentication successful", 200
        )


class DynamicUploadViewSet(cust_view.IddecodeModelViewSet):
    """A simple ViewSet for viewing and editing the Dynamic Upload template of
    node."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )
    serializer_class = temp_ser.TxnBulkSerializer


class TemplateFieldList(generics.ListAPIView):
    """API to list the template type fields in a template and create template
    fields."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = temp_ser.TemplateTypeFieldSerializer

    def get_queryset(self, *args, **kwargs):
        """To perform function get_queryset."""
        temp_type = self.kwargs["type"]
        return temp_models.TemplateTypeField.objects.filter(
            template_type__in=temp_type
        )
