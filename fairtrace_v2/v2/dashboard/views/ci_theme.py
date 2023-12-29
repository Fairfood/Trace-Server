"""Views related to themes are defined here."""
import re

from common import library as comm_lib
from common.exceptions import AccessForbidden
from common.exceptions import NotFound
from common.library import success_response
from rest_framework import generics
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from v2.accounts import permissions as user_permissions
from v2.accounts.constants import USER_TYPE_FAIRFOOD_ADMIN
from v2.dashboard import filters
from v2.dashboard.models import CITheme
from v2.dashboard.models import ConsumerInterfaceProduct
from v2.dashboard.models import ConsumerInterfaceStage
from v2.dashboard.models import MenuItem
from v2.dashboard.serializers.theme import CIThemeSerializer
from v2.dashboard.serializers.theme import CIValidateBatchSerializer
from v2.dashboard.serializers.theme import ConsumerInterfaceProductSerializer
from v2.dashboard.serializers.theme import ConsumerInterfaceStageSerializer
from v2.dashboard.serializers.theme import MenuItemSerializer
from v2.dashboard.serializers.theme import PublicThemeSerializer
from v2.supply_chains import permissions as sc_permissions


class PublicThemeDetails(generics.RetrieveUpdateAPIView):
    """API to get theme details from consumer interface."""

    permission_classes = (user_permissions.CIValidTOTP,)

    serializer_class = PublicThemeSerializer
    queryset = CITheme.objects.all()
    lookup_field = "name"


class ValidateName(APIView):
    """API to validate name."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )

    @staticmethod
    def post(request, *args, **kwargs):
        """Function to get theme name availability."""
        name = request.data["name"]
        if not re.match("^[A-Za-z0-9-]*$", name):
            raise ValidationError(
                "Theme name can have only letters, numbers or hyphen(-)."
            )
        if CITheme.objects.filter(name=name).exists():
            raise ValidationError("Theme name already taken.")

        return comm_lib._success_response({}, "Theme name available.", 200)


class ValidateBatch(generics.CreateAPIView):
    """API to validate batches."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )

    serializer_class = CIValidateBatchSerializer


class CIThemeListCreateAPI(generics.ListCreateAPIView):
    """API for listing CI themes."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )

    serializer_class = CIThemeSerializer

    filterset_class = filters.CIThemeFilter

    def get_queryset(self):
        """Returns filtered qs."""
        if "node" in self.kwargs and self.kwargs["node"]:
            return self.kwargs["node"].themes.all()
        elif self.kwargs["user"].type == USER_TYPE_FAIRFOOD_ADMIN:
            return CITheme.objects.all()
        else:
            return CITheme.objects.none()

    def get_object(self):
        """returns the retrieved objects."""
        theme_ptr = self.kwargs["pk"]
        if theme_ptr == "default":
            return CITheme.objects.filter(is_public=True).first()
        try:
            return CITheme.objects.get(id=comm_lib._decode(theme_ptr))
        except CITheme.DoesNotExist:
            raise NotFound


class CIThemeRetrieveUpdateDestroyAPI(generics.RetrieveUpdateDestroyAPIView):
    """APIs for consumer interface theme."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )

    serializer_class = CIThemeSerializer

    def get_queryset(self):
        """Returns the filtered qs."""
        if "node" in self.kwargs:
            return self.kwargs["node"].themes.all()
        elif self.kwargs["user"].type == USER_TYPE_FAIRFOOD_ADMIN:
            return CITheme.objects.all()
        else:
            return CITheme.objects.none()

    def get_object(self):
        """Returns the retrieve object."""
        theme_ptr = self.kwargs["pk"]
        if theme_ptr == "default":
            return CITheme.objects.filter(is_public=True).first()
        try:
            return CITheme.objects.get(id=comm_lib._decode(theme_ptr))
        except CITheme.DoesNotExist:
            raise NotFound

    def delete(self, request, *args, **kwargs):
        """To delete theme objects."""
        theme = self.get_object()
        if theme.is_public:
            raise AccessForbidden("Default theme cannot be deleted")
        return super(CIThemeRetrieveUpdateDestroyAPI, self).delete(
            request, *args, **kwargs
        )


class CreateCIProduct(generics.CreateAPIView):
    """View to add Consumer Interface Product."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )

    serializer_class = ConsumerInterfaceProductSerializer


class RetrieveUpdateDeleteCIProduct(generics.RetrieveUpdateDestroyAPIView):
    """View to add Consumer Interface Product."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )

    queryset = ConsumerInterfaceProduct.objects.all()
    serializer_class = ConsumerInterfaceProductSerializer


class CreateCIStage(generics.CreateAPIView):
    """View to add Consumer Interface Stage."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )

    serializer_class = ConsumerInterfaceStageSerializer


class RetrieveUpdateDeleteCIStage(generics.RetrieveUpdateDestroyAPIView):
    """View to add Consumer Interface Stage."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )
    queryset = ConsumerInterfaceStage.objects.all()

    serializer_class = ConsumerInterfaceStageSerializer


class CreateCIMenuItem(generics.CreateAPIView):
    """View to add Consumer Interface Stage."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )

    serializer_class = MenuItemSerializer


class RetrieveUpdateDeleteCIMenuItem(generics.RetrieveUpdateDestroyAPIView):
    """View to add Consumer Interface Stage."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccessOrIsFairfoodAdmin,
    )
    queryset = MenuItem.objects.all()

    serializer_class = MenuItemSerializer


class CIThemeLanguageViewSet(viewsets.ViewSet):
    """API ViewSet for retrieving CI theme languages.

    This ViewSet allows retrieving information about CI theme languages.
    It requires valid CI TOTP authentication.
    """

    permission_classes = (user_permissions.CIValidTOTP,)

    @staticmethod
    def retrieve(request, language=None, pk=None):
        """Retrieve CI theme languages.

        This method retrieves the language information for a CI theme
        specified by the primary key (pk). It returns the default language
        and the available languages for the theme.

        Parameters:
        - request: The HTTP request object.
        - language: The language code (not used in this method).
        - pk: The primary key of the CI theme.

        Returns:
        - Response: The response containing the language information.
        """
        queryset = CITheme.objects.all()
        theme = get_object_or_404(queryset, name=pk)
        data = {
            "default_language": theme.default_language,
            "available_languages": theme.available_languages,
        }

        return success_response(data)
