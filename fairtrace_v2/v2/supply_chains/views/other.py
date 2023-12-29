"""General API returning static data."""
from common.country_data import COUNTRIES
from common.drf_custom.views import IdencodeObjectViewSetMixin
from common.library import success_response
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from v2.accounts import permissions as user_permissions
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.models.profile import FarmerAttachment
from v2.supply_chains.models.profile import FarmerPlot
from v2.supply_chains.models.profile import FarmerReference
from v2.supply_chains.models.profile import Reference
from v2.supply_chains.serializers.other import FarmerAttachmentSerializer
from v2.supply_chains.serializers.other import FarmerPlotSerializer
from v2.supply_chains.serializers.other import FarmerReferenceSerializer
from v2.supply_chains.serializers.other import ReferenceSerializer


class CountryData(APIView):
    """API view for retrieving country data.

    This view returns the data for countries. The class inherits from the
    APIView class provided by the Django REST Framework, which allows defining
    API endpoints.

    TODO: require TOTP
    """

    @staticmethod
    def get(request, *args, **kwargs):
        """Returns the country data."""
        return success_response(COUNTRIES)


class ReferenceViewSet(IdencodeObjectViewSetMixin, viewsets.ModelViewSet):
    """APIs for reference model."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )
    queryset = Reference.objects.all()
    serializer_class = ReferenceSerializer
    allowed_methods = ("GET",)

    def get_queryset(self):
        """To include backend filtering."""
        return (
            super(ReferenceViewSet, self)
            .get_queryset()
            .filter_by_query_params(self.request)
        )


class FarmerReferenceViewSet(
    IdencodeObjectViewSetMixin, viewsets.ModelViewSet
):
    """APIs for reference model."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )
    queryset = FarmerReference.objects.all()
    serializer_class = FarmerReferenceSerializer

    def get_queryset(self):
        """To include backend filtering."""
        return (
            super(FarmerReferenceViewSet, self)
            .get_queryset()
            .filter_by_query_params(self.request)
        )

    def create(self, request, *args, **kwargs):
        """To alter request data to add information."""
        self._inject_node(**kwargs)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Check with is_editable key."""
        self._check_is_editable()
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Check with is_editable key."""
        self._check_is_editable()
        return super().destroy(request, *args, **kwargs)

    def _inject_node(self, **kwargs):
        """To insert current node as source."""
        node = kwargs.get("node")

        # Only proceed if node is available.
        if not node:
            return
        set_mutable = False

        # Check for mutable flag present for request data.
        if hasattr(self.request.data, "_mutable"):
            set_mutable = True

        if set_mutable:
            mutable = self.request.data._mutable
            # set data as mutable
            self.request.data._mutable = True
            self.request.data["source"] = node.idencode
            # restore to original
            self.request.data._mutable = mutable
        else:
            self.request.data["source"] = node.idencode

    def _check_is_editable(self):
        """To check this reference is editable or not."""
        instance = self.get_object()
        if not instance.reference.is_editable:
            raise ValidationError(
                detail="This reference is not editable by " "user."
            )


class FarmerPlotViewSet(IdencodeObjectViewSetMixin, ModelViewSet):
    """Viewset for managing farmer plots.

    This viewset provides APIs for creating, retrieving, updating, and
    deleting farmer plots. It inherits from the
    IdencodeObjectViewSetMixin, which includes ID encryption and
    decryption functionality, and the ModelViewSet, which provides
    default implementation for CRUD operations.
    """

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )
    queryset = FarmerPlot.objects.all()
    serializer_class = FarmerPlotSerializer

    def get_queryset(self):
        """Including manager filters."""
        return super().get_queryset().filter_by_query_params(self.request)


class FarmerAttachmentViewSet(IdencodeObjectViewSetMixin, ModelViewSet):
    """Viewset for managing farmer attachments.

    This viewset provides APIs for creating, retrieving, updating, and
    deleting farmer attachments. It inherits from the
    IdencodeObjectViewSetMixin, which includes ID encryption and
    decryption functionality, and the ModelViewSet, which provides
    default implementation for CRUD operations.
    """

    queryset = FarmerAttachment.objects.all()
    serializer_class = FarmerAttachmentSerializer

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeWriteAccess,
    )

    def get_queryset(self):
        """Retrieve the queryset of FarmerAttachment objects.

        Returns:
        - QuerySet: The filtered queryset of FarmerAttachment objects.
        """
        queryset = super(FarmerAttachmentViewSet, self).get_queryset()
        return queryset.filter_by_query_params(self.request)

    def create(self, request, *args, **kwargs):
        """Create a new farmer attachment.

        Injects the node associated with the request and calls the
        create method of the parent class.
        """
        self.inject_node(request)
        return super(FarmerAttachmentViewSet, self).create(
            request, *args, **kwargs
        )

    def update(self, request, *args, **kwargs):
        """Update an existing farmer attachment.

        Injects the node associated with the request and calls the
        update method of the parent class.
        """
        self.inject_node(request)
        return super(FarmerAttachmentViewSet, self).update(
            request, *args, **kwargs
        )

    @staticmethod
    def inject_node(request):
        """Add node to the request data."""
        node = request.parser_context["kwargs"].get("node", None)
        set_mutable = False

        # Check for mutable flag present for request data.
        if hasattr(request.data, "_mutable"):
            set_mutable = True

        if set_mutable:
            mutable = request.data._mutable
            # set data as mutable
            request.data._mutable = True
            request.data["node"] = node.idencode
            request.data["creator"] = request.user.idencode
            # restore to original
            request.data._mutable = mutable
        else:
            request.data["node"] = node
            request.data["creator"] = request.user.idencode
