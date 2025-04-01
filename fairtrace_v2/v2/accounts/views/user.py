"""Views related to user account and tokens."""
from common.drf_custom.views import MultiPermissionView
from rest_framework import generics
from rest_framework import viewsets
from rest_framework import status
from rest_framework.permissions import IsAuthenticated as BaseIsAuthenticated
from rest_framework.decorators import permission_classes
from common.library import success_response
from common.backends.sso import SSORequest
from v2.accounts import permissions as user_permissions
from v2.accounts.constants import USER_TYPE_NODE_USER
from v2.accounts.filters import UserFilter
from v2.accounts.models import FairfoodUser
from v2.accounts.models import TermsAndConditions
from v2.accounts.permissions import IsAuthenticated
from v2.accounts.serializers import user as user_serializers
from v2.supply_chains.permissions import IsFairfoodAdmin


# accounts/user/<id:optional>/


class UserDetails(
    generics.RetrieveUpdateAPIView, generics.ListAPIView, MultiPermissionView
):
    """View to update user details."""

    # TODO: user details fetch without id
    http_method_names = ["get", "patch"]

    permissions = {
        "GET": (user_permissions.IsAuthenticated,),
        "PATCH": (
            user_permissions.IsAuthenticated,
            user_permissions.HasUserAccess,
        ),
    }

    serializer_class = user_serializers.UserSerializer
    queryset = FairfoodUser.objects.all()


class CurrentUser(generics.RetrieveAPIView):
    """Get current user details."""

    permission_classes = (BaseIsAuthenticated,)
    serializer_class = user_serializers.UserSerializer

    def get_object(self):
        """Get current user object."""
        return self.request.user


class UserList(generics.ListAPIView):
    """List users."""

    # TODO: change url
    permission_classes = (user_permissions.IsAuthenticated,)
    serializer_class = user_serializers.UserListSerializer
    # TODO: use user serializer with min_mode

    filterset_class = UserFilter
    queryset = FairfoodUser.objects.all()


class TermsAndConditionsDetails(generics.ListAPIView):
    """API to get latest terms and conditions."""

    permission_classes = (user_permissions.ValidTOTP,)

    serializer_class = user_serializers.TermsAndConditionsSerializer

    def get_queryset(self):
        """To perform function get_object."""
        return TermsAndConditions.objects.filter(
            default=True).order_by().distinct(
            "default", )


class AdminUserViewSet(viewsets.ModelViewSet):
    """Class to handle AdminUserViewSet and functions."""

    permission_classes = (IsAuthenticated, IsFairfoodAdmin)
    queryset = FairfoodUser.objects.exclude(type=USER_TYPE_NODE_USER)
    serializer_class = user_serializers.UserListSerializer
    filterset_class = UserFilter

    def get_serializer_class(self):
        """Switch serializer class."""
        if self.request.method == "POST":
            return user_serializers.UserSerializer
        return super(AdminUserViewSet, self).get_serializer_class()
    
    def create(self, request, *args, **kwargs):
        email = request.data.get("email")
        user = FairfoodUser.objects.filter(email=email)
        if user.exists():
            user.update(**request.data)
            sso = SSORequest()
            sso.update_user(user.first())
            return success_response("Updated successfully", 
                                    status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)
