"""View for products in the project."""
from common.library import unix_to_datetime
from django.db.models import Q
from rest_framework import generics
from v2.accounts import permissions as user_permissions
from v2.projects.models import Project
from v2.projects.serializers import project as project_ser
from v2.supply_chains import permissions as sc_permissions


class ProjectProductListAPI(generics.ListAPIView):
    """API to list the products in a project."""

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )

    serializer_class = project_ser.ProjectProductSerializer
    is_active = False

    def list(self, request, *args, **kwargs):
        """'is_active' parameter is added with request to separate products
        with grades.

        If 'is_active' is not given then the default value will be
        False.
        """
        is_active = request.query_params.get("is_active", "false")
        self.is_active = True if is_active == "true" else False
        return super(ProjectProductListAPI, self).list(
            request, *args, **kwargs
        )

    def get_queryset(self):
        """To perform function get_queryset."""
        pk = self.kwargs["pk"]
        # status expected values => 'all', 'active', 'inactive'
        status = self.request.query_params.get("status", "inactive")
        updated_after = self.request.query_params.get("updated_after", None)
        project = Project.objects.get(id=pk)
        products = project.product_objects.all()
        if updated_after:
            updated_on = unix_to_datetime(updated_after)
            products = products.filter(
                Q(updated_on__gte=updated_on)
                | Q(premiums__updated_on__gte=updated_on)
            ).distinct()
        if status.lower() != "all":
            if status.lower() == "active":
                return products.filter(is_active=True)
            else:
                # Hardcoded name-set
                ids = [1]
                return products.filter(Q(Q(is_active=False) | Q(id__in=ids)))
        return products
