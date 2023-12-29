from modeltranslation.translator import TranslationOptions
from modeltranslation.translator import translator
from v2.dashboard.models import CITheme, ConsumerInterfaceClaimIntervention
from v2.dashboard.models import ConsumerInterfaceActor
from v2.dashboard.models import ConsumerInterfaceClaim
from v2.dashboard.models import ConsumerInterfaceProduct
from v2.dashboard.models import ConsumerInterfaceStage
from v2.dashboard.models import Program
from v2.dashboard.models import ProgramStat


class CIThemeTranslateFields(TranslationOptions):
    """Class to handle CIThemeTranslateFields and functions."""

    fields = (
        "share_facebook_body",
        "share_facebook_title",
        "share_linkedin_body",
        "share_linkedin_title",
        "share_twitter_body",
        "share_twitter_title",
        "share_whatsapp_body",
        "share_whatsapp_title",
        "video_description",
        "video_title",
        "video_url",
        "banner_text",
        "action_button_text",
        "brand_name",
        "farmer_description",
    )
    # fallback_values = _('-- sorry, no translation provided --')


class ConsumerInterfaceProductTranslateFields(TranslationOptions):
    """Class to handle ConsumerInterfaceProductTranslateFields and
    functions."""

    fields = ("description", "name")
    # fallback_values = _('-- sorry, no translation provided --')


class ConsumerInterfaceActorTranslateFields(TranslationOptions):
    """Class to handle ConsumerInterfaceActorTranslateFields and functions."""

    fields = ("description", "name")
    # fallback_values = _('-- sorry, no translation provided --')


class ConsumerInterfaceClaimTranslateFields(TranslationOptions):
    """Class to handle ConsumerInterfaceClaimTranslateFields and functions."""

    fields = ("description",)
    # fallback_values = _('-- sorry, no translation provided --')


class ConsumerInterfaceClaimInterventionTranslateFields(TranslationOptions):
    """Class to handle ConsumerInterfaceClaimTranslateFields and functions."""

    fields = ("name", "description")
    # fallback_values = _('-- sorry, no translation provided --')


class ConsumerInterfaceStageTranslateFields(TranslationOptions):
    """Class to handle ConsumerInterfaceStageTranslateFields and functions."""

    fields = ("description", "actor_name", "title")
    # fallback_values = _('-- sorry, no translation provided --')


class ProgramTranslateFields(TranslationOptions):
    """Class to handle ProgramTranslateFields and functions."""

    fields = ("description", "title")
    # fallback_values = _('-- sorry, no translation provided --')


class ProgramStatTranslateFields(TranslationOptions):
    """Class to handle ProgramStatTranslateFields and functions."""

    fields = ("name",)
    # fallback_values = _('-- sorry, no translation provided --')


translator.register(CITheme, CIThemeTranslateFields)
translator.register(
    ConsumerInterfaceProduct, ConsumerInterfaceProductTranslateFields
)
translator.register(
    ConsumerInterfaceStage, ConsumerInterfaceStageTranslateFields
)
translator.register(Program, ProgramTranslateFields)
translator.register(ProgramStat, ProgramStatTranslateFields)
translator.register(
    ConsumerInterfaceActor, ConsumerInterfaceActorTranslateFields
)
translator.register(
    ConsumerInterfaceClaim, ConsumerInterfaceClaimTranslateFields
)
translator.register(
    ConsumerInterfaceClaimIntervention,
    ConsumerInterfaceClaimInterventionTranslateFields
)
