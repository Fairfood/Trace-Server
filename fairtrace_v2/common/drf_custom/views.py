"""Comming Base Views."""
from common import library as comm_lib
from common.exceptions import BadRequest
from common.library import decode
from rest_framework import viewsets
from rest_framework.views import APIView


class MultiPermissionView(APIView):
    """Permissions can be defined using permissions attribute with a dictionary
    with the type of request as key and permission as value."""

    permissions = {}

    def get_permissions(self):
        """Get permissions."""
        try:
            self.permission_classes = self.permissions[self.request.method]
        except KeyError:
            raise BadRequest("Method not allowed")
        return super(MultiPermissionView, self).get_permissions()


class IddecodeModelViewSet(viewsets.ModelViewSet):
    """Idencode compatible viewset."""

    def get_object(self):
        """Get object."""
        return self.basename.objects.get(
            pk=comm_lib._decode(self.kwargs["pk"])
        )


# pytype: disable=attribute-error
class IdencodeObjectViewSetMixin:
    """A Mixin for converting lookup. Expecting HashID.

    IMPORTANT: Give priority while subclassing in ViewSets.

    Initially DRF is not supporting url conversion in Routers.
    """

    def get_object(self):
        """Change lookup to a decoded value before processing."""
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        value = self.kwargs.get(lookup_url_kwarg, None)
        if value:
            # check decode successful else continue with initial value
            new_value = decode(value)
            if new_value:
                self.kwargs[lookup_url_kwarg] = new_value
        return super(IdencodeObjectViewSetMixin, self).get_object()
