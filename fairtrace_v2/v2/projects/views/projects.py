"""View for project details related APIs."""
import json

from common import library as comm_lib
from common import vendors
from common.drf_custom.views import IdencodeObjectViewSetMixin
from common.exceptions import BadRequest
from common.library import success_response
from django.db.models import Q
from rest_framework import generics
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from sentry_sdk import capture_message
from v2.accounts import permissions as user_permissions
from v2.projects import constants as proj_consts
from v2.projects import filters
from v2.projects import permissions as proj_permissions
from v2.projects.constants import INCOMING
from v2.projects.constants import PAYMENT_DIRECTION_CHOICES
from v2.projects.models import NodeCard
from v2.projects.models import Payment
from v2.projects.models import Project
from v2.projects.models import ProjectPremium
from v2.projects.serializers import project
from v2.projects.serializers.project import PaymentSerializer
from v2.projects.serializers.project import ProjectPremiumSerializer
from v2.supply_chains import permissions as sc_permissions
from common.library import decode
from .. import tasks


class ProjectDetailsAPI(generics.RetrieveAPIView):
    """Class to handle ProjectDetailsAPI and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = project.ProjectSerializer

    def get_queryset(self):
        """To perform function get_queryset."""
        node = self.kwargs["node"]
        query = Q(owner=node) | Q(member_nodes=node)
        return (
            Project.objects.filter(query)
            .order_by()
            .order_by("id")
            .distinct("id")
        )


class ProjectPremiumViewSet(ModelViewSet):
    """APIs for premiums."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )

    queryset = ProjectPremium.objects.all()
    serializer_class = ProjectPremiumSerializer
    allowed_methods = ["get"]

    def get_queryset(self):
        """Including manager filters."""
        return super().get_queryset().filter_by_query_params(self.request)


class CardAPI(generics.ListCreateAPIView):
    """Class to handle CardAPI and functions."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
        proj_permissions.HasProjectAccess,
    )

    serializer_class = project.NodeCardSerializer

    filterset_class = filters.FilterCards

    def get_queryset(self):
        """To perform function get_queryset."""
        project = self.kwargs["project"]
        node = self.kwargs["node"]
        suppliers = node.get_suppliers(supply_chain=project.supply_chain)
        proj_suppliers = project.member_nodes.filter(id__in=suppliers)
        return NodeCard.objects.filter(node__in=proj_suppliers)


class TestSMSAPIView(APIView):
    """View to test APIs."""

    http_method_names = ["post"]

    @staticmethod
    def post(request):
        """To receive sms trigger."""
        data = json.loads(request.body)
        sender = "+6285574670328"
        capture_message(data)
        capture_message(str(data["body"]) == "2020")
        if str(data["body"]) == "2020":
            capture_message("2020 found sending smsm")
            receipiant = data["originator"]
            if not (receipiant.startswith("+")):
                receipiant = f"+{receipiant}"
            if receipiant.startswith("+31"):
                sender = "+3197010240770"
            capture_message(receipiant)
            vendors.send_farmer_sms(
                receipiant, proj_consts.SMS_FARMER_BAL, sender
            )
        return comm_lib._success_response({}, "trigger success", 200)


class AppLogin(generics.CreateAPIView):
    """App login view."""

    serializer_class = project.AppLoginSerializer


class AppLogout(APIView):
    """View to logout."""

    permission_classes = (user_permissions.IsAuthenticated,)
    http_method_names = [
        "post",
    ]

    def post(self, request, user=None, *args, **kwargs):
        """Post method to app logout.

        Request Params:
            Body:
                device_id(str): optional device id to delete device.
            kwargs:
                account(obj): user account.
        Response:
            Success response.
        """
        device_id = request.data.get("device_id", None)
        if not device_id:
            raise BadRequest("device_id is required")
        user.app_logout(device_id)

        return comm_lib._success_response({}, "Logout successful", 200)


class PaymentViewSet(IdencodeObjectViewSetMixin, ModelViewSet):
    """APIs to manage payments."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    allowed_methods = ["post", "get"]

    def get_queryset(self):
        """Including manager filters."""
        return super().get_queryset().filter_by_query_params(self.request)

    def create(self, request, *args, **kwargs):
        """To separate send and receive."""
        payment_direction = request.data.pop("direction", None)

        # Checking payment direction
        if (
            not payment_direction
            or payment_direction
            not in dict(PAYMENT_DIRECTION_CHOICES).values()
        ):
            raise ValidationError(
                detail="a valid payment direction is " "required."
            )

        self._inject_actor(payment_direction, **kwargs)
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["patch"])
    def invoice(self, request, **kwargs):
        """Adding separate API for uploading invoice."""

        # getting file from request.
        invoice = request.data.get("invoice")
        if not invoice and not invoice.file:
            raise ValidationError("No invoice attached.")

        # Using serializer to update with instance
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data={"invoice": invoice, "updator": request.user},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(
            {"id": instance.idencode, "invoice": instance.invoice.url}
        )

    def _inject_actor(self, payment_direction, **kwargs):
        """To insert current node against payment direction."""
        node = kwargs["node"]

        # Only proceed if node is available.
        if not node:
            return
        set_mutable = False

        # set filed to inject
        field = "destination" if payment_direction == INCOMING else "source"

        # Check for mutable flag present for request data.
        if hasattr(self.request.data, "_mutable"):
            set_mutable = True

        if set_mutable:
            mutable = self.request.data._mutable
            # set data as mutable
            self.request.data._mutable = True
            self.request.data[field] = node.idencode
            # restore to original
            self.request.data._mutable = mutable
        else:
            self.request.data[field] = node.idencode


class FanalSyncView(APIView):
    """View to sync fanal data."""
     
    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )

    def post(self, request, *args, **kwargs):
        """To sync fanal data."""
        project_id = request.data.get("project", None)
        node = kwargs.get("node", None)
        if not node:
            raise BadRequest("node is not provided in the headers")
        if not project_id:
            raise BadRequest("project is required")
        project = Project.objects.filter(id=decode(project_id)).first()
        if not project:
            raise BadRequest("project not found")
        task = tasks.final_sync.delay(node.id, project.owner.id)
        request.user.is_active = False
        request.user.save()
        return success_response({"task_id": task.task_id})
