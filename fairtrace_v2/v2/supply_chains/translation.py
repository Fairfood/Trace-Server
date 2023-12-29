from modeltranslation.translator import TranslationOptions
from modeltranslation.translator import translator
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Node
from v2.supply_chains.models import Operation


class OperationTranslateFields(TranslationOptions):
    """Class to handle OperationTranslateFields and functions."""

    fields = ("name",)
    # fallback_values = _('-- sorry, no translation provided --')


class NodeTranslateFields(TranslationOptions):
    """Class to handle NodeTranslateFields and functions."""

    fields = ("description_basic",)
    # fallback_values = _('-- sorry, no translation provided --')


class CompanyFields(TranslationOptions):
    """Class to handle CompanyFields and functions."""

    fields = ("name",)
    # fallback_values = _('-- sorry, no translation provided --')


class FarmerFields(TranslationOptions):
    """Class to handle FarmerFields and functions."""

    fields = ("first_name", "last_name")
    # fallback_values = _('-- sorry, no translation provided --')


translator.register(Operation, OperationTranslateFields)
translator.register(Node, NodeTranslateFields)
translator.register(Company, CompanyFields)
translator.register(Farmer, FarmerFields)
