"""Models for dashboard."""
import copy
import re

from common.library import _get_file_path
from common.library import _percentage
from common.models import AbstractBaseModel
from django.conf import settings
from django.contrib.postgres import fields
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils import translation
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _
from v2.claims.models import Claim
from v2.dashboard import constants as ds_constants
from v2.supply_chains import constants as sc_constants
from v2.supply_chains.models import Node


# Create your models here.


class DashboardTheme(AbstractBaseModel):
    """Variables for the consumer interface theme."""

    # Node
    node = models.OneToOneField(
        "supply_chains.Node",
        null=True,
        default=None,
        on_delete=models.CASCADE,
        related_name="dashboard_theme",
    )
    # name = models.CharField(max_length=100, null=True, blank=True)
    default = models.BooleanField(default=False)
    # Brand Details
    image = models.FileField(upload_to=_get_file_path, blank=True, null=True)

    # Colours
    colour_primary_alpha = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_primary_beta = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_primary_gamma = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_primary_delta = models.CharField(
        default="", null=True, blank=True, max_length=20
    )

    colour_secondary = models.CharField(
        default="", null=True, blank=True, max_length=20
    )

    colour_font_alpha = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_font_beta = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_font_negative = models.CharField(
        default="", null=True, blank=True, max_length=20
    )

    colour_border_alpha = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_border_beta = models.CharField(
        default="", null=True, blank=True, max_length=20
    )

    colour_background = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_sidebar = models.CharField(
        default="", null=True, blank=True, max_length=20
    )

    colour_map_background = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_map_clustor = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_map_marker = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_map_selected = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    colour_map_marker_text = models.CharField(
        default="", null=True, blank=True, max_length=20
    )

    def __str__(self):
        """To perform function __str__."""
        try:
            return "%s : %d" % (self.node.full_name, self.id)
        except Exception:
            return f"Theme : {self.id}"


class Program(AbstractBaseModel):
    """To show the program part of new version of CI."""

    title = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.title} : {self.pk}"


class ProgramStat(AbstractBaseModel):
    """
    To show dynamic status items against program
        'is_visible' : To show whether the item is visible or not
    """

    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name="program_stats"
    )
    name = models.CharField(max_length=250)
    value = models.FloatField(default=0)
    symbol = models.CharField(max_length=5, null=True, blank=True)
    is_visible = models.BooleanField(default=True)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.name}-{self.value} : {self.pk})"


class CITheme(AbstractBaseModel):
    """Variables for the consumer interface theme."""

    # Node
    name = models.CharField(unique=True, max_length=100, null=True, blank=True)
    node = models.ForeignKey(
        "supply_chains.Node", on_delete=models.CASCADE, related_name="themes"
    )
    supply_chains = models.ManyToManyField(
        "supply_chains.SupplyChain", blank=True, related_name="themes"
    )
    batch = models.ForeignKey(
        "products.Batch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="themes",
    )
    is_public = models.BooleanField(default=False)
    version = models.CharField(max_length=100, default=0)

    # Colours
    primary_colour = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    page_bg_colour = models.CharField(
        default="#FFFFFF", null=True, blank=True, max_length=20
    )
    primary_colour_light = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    primary_colour_shade_1 = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    primary_colour_shade_2 = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    primary_colour_shade_3 = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    primary_colour_shade_4 = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    primary_colour_shade_5 = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    secondary_colour = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    text_colour = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    action_colour = models.CharField(
        default="", null=True, blank=True, max_length=20
    )
    stroke_colour = models.CharField(
        default="", null=True, blank=True, max_length=20
    )

    # Brand Details
    brand_name = models.CharField(
        default="", null=True, blank=True, max_length=100
    )
    brand_logo = models.FileField(upload_to=_get_file_path, blank=True)
    brand_website = models.CharField(
        default="", null=True, blank=True, max_length=500
    )

    # Social Media
    show_brand_footer = models.BooleanField(default=False)
    facebook_url = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    linkedin_url = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    instagram_url = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    twitter_url = models.CharField(
        default="", null=True, blank=True, max_length=500
    )

    # Social sharing options
    share_facebook_title = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    share_facebook_body = models.CharField(
        default="", null=True, blank=True, max_length=2000
    )
    share_linkedin_title = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    share_linkedin_body = models.CharField(
        default="", null=True, blank=True, max_length=2000
    )
    share_twitter_title = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    share_twitter_body = models.CharField(
        default="", null=True, blank=True, max_length=2000
    )
    share_whatsapp_title = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    share_whatsapp_body = models.CharField(
        default="", null=True, blank=True, max_length=2000
    )

    # Action button
    action_button_text = models.CharField(
        default="", null=True, blank=True, max_length=100
    )
    action_button_url = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    show_action_button = models.BooleanField(default=True)
    show_share_button = models.BooleanField(default=True)

    # Video Banner
    video_title = models.CharField(
        default="", null=True, blank=True, max_length=200
    )
    video_url = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    video_description = models.CharField(
        default="", null=True, blank=True, max_length=1000
    )

    # Placeholder images
    product_placeholder = models.FileField(
        upload_to=_get_file_path, blank=True
    )
    farmer_placeholder = models.FileField(upload_to=_get_file_path, blank=True)
    actor_placeholder = models.FileField(upload_to=_get_file_path, blank=True)

    # Page Banner
    banner_text = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    banner_text_colour = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    banner_image = models.FileField(upload_to=_get_file_path, blank=True)
    mobile_banner_image = models.FileField(
        upload_to=_get_file_path, blank=True
    )
    banner_farmer_icon = models.FileField(upload_to=_get_file_path, blank=True)
    banner_mode = models.IntegerField(
        choices=ds_constants.BANNER_WIDTH_CHOICES,
        default=ds_constants.HALF_WIDTH_BANNER,
    )

    available_languages = models.CharField(
        max_length=500, default="en", null=True, blank=True
    )
    default_language = models.CharField(
        max_length=500, default="en", null=True, blank=True
    )
    farmer_description = models.TextField(null=True, blank=True)

    # Claim details
    # To show default claim in consumer-interface new version
    default_claim = models.ForeignKey(
        Claim,
        on_delete=models.SET_NULL,
        related_name="default_claim_themes",
        blank=True,
        null=True,
    )
    # Story project details
    # To show story_project in consumer-interface new version
    program = models.ForeignKey(
        Program,
        on_delete=models.SET_NULL,
        related_name="program_themes",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("id",)

    def __str__(self):
        """To perform function __str__."""
        try:
            return "%s : %d" % (self.name, self.id)
        except Exception:
            return f"Theme : {self.id}"

    def create_copy(self):
        """Create a theme copy."""
        new_theme = copy.deepcopy(self)
        new_theme.id = None
        new_theme.batch = None
        new_theme.is_public = False
        new_theme.name = get_random_string(10)
        new_theme.save()
        for item in self.menu_items.all():
            new_item = copy.deepcopy(item)
            new_item.theme = new_theme
            new_item.id = None
            new_item.save()
        for product in self.products.all():
            new_product = copy.deepcopy(product)
            new_product.theme = new_theme
            new_product.id = None
            new_product.save()
        for stage in self.stages.all():
            new_stage = copy.deepcopy(stage)
            new_stage.theme = new_theme
            new_stage.id = None
            new_stage.save()
        return new_theme

    def is_available_language(self, language):
        """
        Args:
            language (str): Language code eg: 'en'
        """
        return language in self.available_languages.replace(" ", "").split(",")

    def check_language_rollback(self):
        """Rollback to default language."""
        current_language = translation.get_language()
        if not self.is_available_language(current_language):
            translation.activate(self.default_language)

    def clean(self):
        """clean the data before saving."""
        self._clean_available_languages()
        # TODO: Need a proper cleaning is required.
        # self._clean_farmer_description()

    def _clean_available_languages(self):
        """Validating the available_languages field before saving.

        Checking the languages available in the settings.
        """
        available_language_set = set(
            f"{self.available_languages}".strip("[]")
            .replace(" ", "")
            .split(",")
        )
        ci_language_set = set(dict(settings.CI_LANGUAGES).keys())
        if not available_language_set.issubset(ci_language_set):
            error = _("Language(s) not defined in the system")
            raise ValidationError(f"{error}")
        if self.default_language and (
                self.default_language not in available_language_set
        ):
            available_language_set.add(self.default_language)
        self.available_languages = ",".join(available_language_set)

    def _clean_farmer_description(self):
        """Checking if proper placeholdes for 'farmer_name' and 'country'
        included."""
        errors = []
        if self.farmer_description:
            farmer_name = re.compile(r"{\s*farmer_name\s*}", re.IGNORECASE)
            country = re.compile(r"{\s*country\s*}", re.IGNORECASE)
            if not farmer_name.search(f"{self.farmer_description}"):
                errors.append("Include {farmer_name} in farmer_description")
            if not country.search(f"{self.farmer_description}"):
                errors.append("Include {country} in farmer_description")
            if errors:
                raise ValidationError(errors)


class MenuItem(AbstractBaseModel):
    """Model for menu item on the consumer interface page."""

    theme = models.ForeignKey(
        CITheme, on_delete=models.CASCADE, related_name="menu_items"
    )

    title = models.CharField(default="", null=True, blank=True, max_length=100)
    url = models.CharField(default="", null=True, blank=True, max_length=500)
    target = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    position = models.IntegerField(default=0)

    class Meta:
        ordering = ("position",)

    def __str__(self):
        """To perform function __str__."""
        return "%s : %d" % (self.title, self.id)


class ConsumerInterfaceProduct(AbstractBaseModel):
    """Model for product on the consumer interface page."""

    theme = models.ForeignKey(
        CITheme, on_delete=models.CASCADE, related_name="products"
    )
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)

    name = models.CharField(default="", null=True, blank=True, max_length=100)
    image = models.FileField(upload_to=_get_file_path, blank=True)
    description = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    location = models.CharField(
        default="", null=True, blank=True, max_length=200
    )

    def __str__(self):
        """To perform function __str__."""
        return "%s : %d" % (self.name, self.id)

    @property
    def image_url(self):
        """Get image url."""
        if self.image:
            return self.image.url
        elif self.product.image:
            return self.product.image.url
        return ""


class ConsumerInterfaceStage(AbstractBaseModel):
    """Model for product on the consumer interface page."""

    theme = models.ForeignKey(
        CITheme, on_delete=models.CASCADE, related_name="stages"
    )

    title = models.CharField(default="", null=True, blank=True, max_length=100)
    image = models.FileField(upload_to=_get_file_path, blank=True)
    description = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    actor_name = models.CharField(
        default="", null=True, blank=True, max_length=100
    )
    position = models.IntegerField(default=0)
    operation = models.ForeignKey(
        "supply_chains.Operation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="stages",
    )

    # Map config
    map_zoom_level = models.IntegerField(default=0)
    map_latitude = models.FloatField(default=0.0)
    map_longitude = models.FloatField(default=0.0)

    class Meta:
        ordering = ("position",)

    def __str__(self):
        """To perform function __str__."""
        return "%s : %d" % (self.title, self.id)

    @property
    def image_url(self):
        """Get image url."""
        if self.image:
            return self.image.url
        return ""


class ConsumerInterfaceActor(AbstractBaseModel):
    """Model for an actor on the consumer interface page.

    This class represents an actor on the consumer interface page,
    associated with a specific theme and a corresponding node.

    Attributes:
        theme (ForeignKey): The CITheme object representing the theme
                            associated with the actor.
        actor (ForeignKey): The Node object representing the actor
                            associated with the page.
        name (str): The name of the actor.
        image (FileField): The file field for the actor's image.
        description (str): The description of the actor.
    """

    theme = models.ForeignKey(
        CITheme, on_delete=models.CASCADE, related_name="actors"
    )
    actor = models.ForeignKey(Node, on_delete=models.CASCADE)

    name = models.CharField(default="", null=True, blank=True, max_length=100)
    image = models.FileField(upload_to=_get_file_path, blank=True)
    description = models.CharField(
        default="", null=True, blank=True, max_length=500
    )

    def __str__(self):
        """To perform function __str__."""
        return f"{self.name} : {self.pk}"

    @property
    def image_url(self):
        """Get image url."""
        if self.image:
            return self.image.url
        elif self.actor.image:
            return self.actor.image.url
        return ""


class ConsumerInterfaceClaim(AbstractBaseModel):
    """Model for a claim on the consumer interface page.

    This class represents a claim on the consumer interface page, associated
    with a specific theme and a corresponding claim.

    Attributes:
        theme (ForeignKey): The CITheme object representing the theme
                            associated with the claim.
        claim (ForeignKey): The Claim object representing the claim associated
                            with the page.
        image (FileField): The file field for the claim's image.
        description (str): The description of the claim.
    """

    theme = models.ForeignKey(
        CITheme, on_delete=models.CASCADE, related_name="claims"
    )
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE)
    image = models.FileField(upload_to=_get_file_path, blank=True)
    description = models.CharField(
        default="", null=True, blank=True, max_length=500
    )
    external_link = models.URLField(null=True, blank=True)

    def __str__(self):
        """To perform function __str__."""
        return "%s : %d" % (self.claim.name, self.pk)

    @property
    def image_url(self):
        """Get image url."""
        if self.image:
            return self.image.url
        return ""


class ConsumerInterfaceClaimIntervention(AbstractBaseModel):
    """
    Represents an intervention associated with a consumer interface claim.

    An intervention is an action or step taken in response to a consumer
    interface claim. It may have a name, description, and an optional image.

    Attributes:
        ci_claim (ForeignKey to ConsumerInterfaceClaim):
            The consumer interface claim to which this intervention is linked.

        name (str):
            The name or title of the intervention (maximum 100 characters).

        description (str, optional):
            A detailed description of the intervention (nullable and blank).

        image (FileField, optional):
            An optional image or file associated with the intervention.
    """
    ci_claim = models.ForeignKey(ConsumerInterfaceClaim,
                                 on_delete=models.CASCADE,
                                 related_name="interventions")
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    image = models.FileField(upload_to=_get_file_path, blank=True)
    external_link = models.URLField(null=True, blank=True)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.name} : {self.pk}"

    @property
    def image_url(self):
        """Get image url."""
        if self.image:
            return self.image.url
        return ""


class NodeStats(AbstractBaseModel):
    """Model to store dashboard stats.

    It needs to be reset when any of the value changes
    """

    node = models.OneToOneField(
        "supply_chains.Node", on_delete=models.CASCADE, related_name="stats"
    )

    last_updated = models.DateTimeField(default=None, null=True, blank=True)
    is_outdated = models.BooleanField(default=True)
    outdated_by = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.SET_NULL,
        related_name="stats_reset",
        null=True,
        blank=True,
        default=None,
    )
    outdated_at = models.DateTimeField(default=None, null=True, blank=True)

    supply_chain_count = models.IntegerField(default=0)
    traceable_chains = models.IntegerField(default=0)
    tier_count = models.IntegerField(default=0)
    chain_length = models.FloatField(default=0.0)
    actor_count = models.IntegerField(default=0)
    supplier_count = models.IntegerField(default=0)
    farmer_count = models.IntegerField(default=0)
    invited_actor_count = models.IntegerField(default=0)
    mapped_actor_count = models.IntegerField(default=0)
    active_actor_count = models.IntegerField(default=0)
    pending_invite_count = models.IntegerField(default=0)

    operation_stats = fields.JSONField(null=True, blank=True, default=dict)
    supplier_coorinates = fields.JSONField(null=True, blank=True, default=dict)
    farmer_coorinates = fields.JSONField(null=True, blank=True, default=dict)

    buyer_ids = fields.JSONField(null=True, blank=True, default=list)
    supplier_ids = fields.JSONField(null=True, blank=True, default=list)
    farmer_ids = fields.JSONField(null=True, blank=True, default=list)

    @property
    def company_count(self):
        """Get company count."""
        return self.actor_count - self.farmer_count

    @property
    def traceable_chain_percent(self):
        """get traceable chain %."""
        return _percentage(self.traceable_chains, self.supply_chain_count)

    def outdate(self, outdated_by=None):
        """Make item Outdated."""
        self.is_outdated = True
        self.outdated_at = timezone.now()
        self.outdated_by = outdated_by
        self.save()

    @staticmethod
    def _operation_count(queryset, supply_chain=None):
        """To perform function _operation_count."""
        operation_count = {"supplier": {}, "farmer": {}}
        for item in queryset:
            nodesupplychains = item.nodesupplychain_set.all()
            if supply_chain:
                nodesupplychains = item.nodesupplychain_set.filter(
                    supply_chain=supply_chain
                )
            for nsc in nodesupplychains:
                if not nsc.primary_operation:
                    continue
                op_id = nsc.primary_operation.id
                nt = nsc.primary_operation.node_type
                node_type = (
                    "supplier"
                    if nt == sc_constants.NODE_TYPE_COMPANY
                    else "farmer"
                )
                if op_id not in operation_count[node_type]:
                    operation_count[node_type][op_id] = {
                        "name": nsc.primary_operation.name,
                        "count": 1,
                    }
                else:
                    operation_count[node_type][op_id]["count"] += 1
        operation_count["farmer"] = list(operation_count["farmer"].values())
        operation_count["supplier"] = list(
            operation_count["supplier"].values()
        )
        return operation_count

    def update_values(self):
        """Update dashboard values."""
        from v2.supply_chains.models import Invitation

        self.supply_chain_count = self.node.supply_chains.count()

        sup_queryset, sup_tier_data = self.node.get_supplier_chain(
            fast_mode=True
        )
        buy_queryset, buy_tier_data = self.node.get_buyer_chain(fast_mode=True)

        sup_ids = sup_queryset.values_list("id", flat=True)
        buy_ids = buy_queryset.values_list("id", flat=True)
        actor_ids = list(sup_ids) + list(buy_ids)
        all_actors = Node.objects.filter(id__in=actor_ids)
        farmers = sup_queryset.filter(type=sc_constants.NODE_TYPE_FARM)
        suppliers = sup_queryset.filter(type=sc_constants.NODE_TYPE_COMPANY)

        comp_ids = [i.id for i in suppliers] + [
            i.id
            for i in buy_queryset.filter(type=sc_constants.NODE_TYPE_COMPANY)
        ]
        comp_ids_incl_self = comp_ids + [self.node.id]
        companies = Node.objects.filter(id__in=comp_ids)
        companies_incl_self = Node.objects.filter(id__in=comp_ids_incl_self)
        invites = Invitation.objects.filter(
            inviter__in=companies_incl_self, invitee__in=companies_incl_self
        )
        sent_invites = invites.filter(email_sent=True)
        signed_up_companies = (
            companies.exclude(invitations_received__in=invites)
            .distinct("id")
            .count()
        )
        invited_actors = companies.filter(
            invitations_received__in=sent_invites
        ).distinct("id")
        active_actors = (
            companies.filter(invitations_received__in=sent_invites)
            .exclude(date_joined=None)
            .distinct("id")
        )

        self.actor_count = all_actors.count()
        self.supplier_count = suppliers.count()
        self.farmer_count = farmers.count()
        self.invited_actor_count = invited_actors.count() + signed_up_companies
        self.active_actor_count = active_actors.count() + signed_up_companies

        self.mapped_actor_count = companies.count() - self.invited_actor_count
        self.pending_invite_count = (
                self.invited_actor_count - self.active_actor_count
        )

        self.farmer_coorinates = list(farmers.values("latitude", "longitude"))
        self.supplier_coorinates = list(
            suppliers.values("latitude", "longitude")
        )

        self.operation_stats = self._operation_count(sup_queryset)

        self.buyer_ids = [i.id for i in buy_queryset]
        self.supplier_ids = [i.id for i in suppliers]
        self.farmer_ids = [i.id for i in farmers]

        tier_counts = [0]
        chain_lengths = []
        traceable_chains = 0
        for nsc in self.node.nodesupplychain_set.all():
            nsc.update_values()
            tier_counts.append(nsc.tier_count)
            if nsc.chain_length:
                chain_lengths.append(nsc.chain_length)
            if nsc.traceable:
                traceable_chains += 1
        self.tier_count = max(tier_counts)
        if chain_lengths:
            self.chain_length = round(
                sum(chain_lengths) / len(chain_lengths), 2
            )
        else:
            self.chain_length = 0
        self.traceable_chains = traceable_chains
        self.is_outdated = False
        self.last_updated = timezone.now()
        self.save()
