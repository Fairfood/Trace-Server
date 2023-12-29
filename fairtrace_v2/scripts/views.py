from django.conf import settings
from django.views.generic.edit import FormView

from .forms import CustomCopySupplyChainForm


class CopySupplyChainView(FormView):
    """Class to handle CopySupplyChainView and functions."""

    form_class = CustomCopySupplyChainForm
    template_name = settings.TEMPLATES_DIR + "/copy_sc_connections.html"
    success_url = "/djadmin-ff/"

    def form_valid(self, form):
        """To perform function orm_valid."""
        node = form.cleaned_data["node"]
        source_supply_chain = form.cleaned_data["source_supply_chain"]
        target_supply_chain = form.cleaned_data["target_supply_chain"]

        form.create_copy_connections(
            node, source_supply_chain, target_supply_chain
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """To perform function get_context_data."""
        context = super().get_context_data(**kwargs)

        # Manually plugging in context variables needed
        # to display necessary links and blocks in the
        # django admin.
        context["title"] = "Copy SupplyChain Connections"
        context["has_permission"] = True
        context["form"] = CustomCopySupplyChainForm()

        return context
