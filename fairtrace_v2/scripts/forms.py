from django import forms
from django.db import transaction as django_transaction
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.models import Node
from v2.supply_chains.models import SupplyChain

from .tasks import copy_connctions


class CustomCopySupplyChainForm(forms.Form):
    """Class for create form for copy connections.

    Set node and supply chain values in dropdown list.
    """

    node = forms.ChoiceField(label="Node ")
    source_supply_chain = forms.ChoiceField(label="Source SupplyChain ")
    target_supply_chain = forms.ChoiceField(label="Target SupplyChain ")

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        super().__init__(*args, **kwargs)
        self.fields["node"].choices = [
            (u.id, str(u))
            for i, u in enumerate(
                Node.objects.select_related("company").filter(
                    type=NODE_TYPE_COMPANY
                )
            )
        ]
        self.fields["node"].initial = Node.objects.select_related(
            "company"
        ).filter(type=NODE_TYPE_COMPANY)
        self.fields["source_supply_chain"].choices = [
            (u.id, str(u)) for i, u in enumerate(SupplyChain.objects.all())
        ]
        self.fields["source_supply_chain"].initial = SupplyChain.objects.all()
        self.fields["target_supply_chain"].choices = [
            (u.id, str(u)) for i, u in enumerate(SupplyChain.objects.all())
        ]
        self.fields["target_supply_chain"].initial = SupplyChain.objects.all()

    @django_transaction.atomic
    def create_copy_connections(
        self, node, source_supply_chain, target_supply_chain
    ):
        """Create copy of connection."""
        django_transaction.on_commit(
            lambda: copy_connctions.delay(
                node, source_supply_chain, target_supply_chain
            )
        )
