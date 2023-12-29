from modeltranslation.translator import TranslationOptions
from modeltranslation.translator import translator
from v2.claims.models import Claim
from v2.claims.models import CriterionField
from v2.claims.models import FieldResponse


class ClaimTranslateFields(TranslationOptions):
    """Class to handle ClaimTranslateFields and functions."""

    fields = ("name", "description_basic", "description_full")
    # fallback_values = _('-- sorry, no translation provided --')


class CriterionFieldTranslateFields(TranslationOptions):
    """Class to handle CriterionFieldTranslateFields and functions."""

    fields = ("title",)
    # fallback_values = _('-- sorry, no translation provided --')


class FieldResponseTranslateFields(TranslationOptions):
    """Class to handle FieldResponseTranslateFields and functions."""

    fields = ("response",)
    # fallback_values = _('-- sorry, no translation provided --')


translator.register(Claim, ClaimTranslateFields)
translator.register(CriterionField, CriterionFieldTranslateFields)
translator.register(FieldResponse, FieldResponseTranslateFields)
