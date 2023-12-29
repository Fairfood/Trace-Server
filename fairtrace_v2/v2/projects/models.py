"""Models for project."""
import re

from common import library
from common.currencies import CURRENCY_CHOICES
from common.library import _get_file_path
from common.models import AbstractBaseModel
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction as db_transaction
from django_extensions.db.fields.json import JSONField
from v2.activity import constants as act_constants
from v2.activity.models import Activity
from v2.projects import constants
from v2.projects.constants import PREMIUM_CATEGORY_CHOICES
from v2.projects.constants import TRANSACTION_PREMIUM
from v2.projects.managers import PaymentQuerySet
from v2.projects.managers import ProjectPremiumQuerySet
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.constants import TRACE_FARMER_REFERENCE_NAME


# Create your models here.


def validate_premium_slab(value):
    """Validates a premium slab value.

    A valid premium slab value is either a single number, decimal number,
    or a range of two numbers separated by a hyphen.

    Args:
        value (str): The premium slab value to validate.

    Raises:
        ValidationError: If the value is not a number or a range
        (without white spaces) in the correct format.
    """
    if not re.match(r"^\d+(\.\d+)?(-\d+(\.\d+)?)?$", value):
        raise ValidationError(
            "Invalid premium slab value: %(value)s. "
            "Please provide either a single number, "
            "decimal number, or a range of two numbers "
            "separated by a hyphen.",
            params={"value": value},
        )


class Project(AbstractBaseModel):
    """Model to store project details. A company can start a project with some
    configurations and add members from their supply chains onto it.

    Attributes:
        name(str)           : Name of the project.
        description(str)    : Description of the project.
        image(file)         : Image of the project.
        owner(obj)          : Node who started the project.
        supply_chain(obj)   : Supply chains that the project runs on.
        members(objs)       : Members in the project (through field).
        products(objs)      : Products in the project (through field).
    """

    name = models.CharField(max_length=100, default="", null=True, blank=True)
    description = models.CharField(
        max_length=2000, default="", null=True, blank=True
    )
    image = models.FileField(
        upload_to=_get_file_path, null=True, blank=True, default=None
    )

    owner = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="owned_projects",
    )
    supply_chain = models.ForeignKey(
        "supply_chains.SupplyChain",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    member_nodes = models.ManyToManyField(
        "supply_chains.Node",
        through="projects.ProjectNode",
        related_name="participating_projects",
    )
    products = models.ManyToManyField(
        "products.Product",
        through="projects.ProjectProduct",
        related_name="projects",
    )
    currency = models.CharField(
        choices=CURRENCY_CHOICES,
        default=None,
        null=True,
        blank=True,
        max_length=5,
    )

    buy_enabled = models.BooleanField(default=True)
    sell_enabled = models.BooleanField(default=False)
    quality_correction = models.BooleanField(default=False)
    show_price_comparison = models.BooleanField(default=True)

    def __str__(self):
        """To perform function __str__."""
        return (
            f"{self.name} {self.owner.full_name} - "
            f"{self.supply_chain.name} | {self.pk}"
        )


class ProjectNode(AbstractBaseModel):
    """Model to store the actors in a project. These actors should be connected
    to the owner of the project in the mentioned supply chain directly or
    indirectly.

    Attributes:
        node(obj)       : Node that is the member of the project
        project(obj)    : Project that the node is a part of
        connection(obj) : Connection by which the node became part of the
                          project Even though it does not provide any
                          additional info. It is added so that the member
                          will be removed from the project is the
                          connections is removed.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="member_objects"
    )
    node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="participating_project_objects",
    )
    connection = models.ForeignKey(
        "supply_chains.Connection",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # TODO: [cyclic] will have to be changed if cyclic connections are
    #  supported.

    def __str__(self):
        """To perform function __str__."""
        return f"{self.project.name} {self.node.full_name} | {self.id}"


class ProjectProduct(AbstractBaseModel):
    """Model to store the products in a project.

    Attributes:
        product(obj)         : Product that is in the project
        project(obj)         : Project that the product is added to
        image(file)          : Image of the product for the project.
        price(float)         : Price of the product. (optional).
        premium(many-to-many): Product specific premiums
        is_active            : To separate products with grade.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="product_objects"
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="project_objects",
    )
    image = models.FileField(
        upload_to=_get_file_path, null=True, default=None, blank=True
    )
    price = models.FloatField(default=None, null=True, blank=True)
    currency = models.CharField(
        choices=CURRENCY_CHOICES,
        default=None,
        null=True,
        blank=True,
        max_length=5,
    )
    premiums = models.ManyToManyField("projects.ProjectPremium", blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.project.name} {self.product.name} | {self.id}"

    def clean(self):
        """clean data."""
        self._clean_premiums()

    def _clean_premiums(self):
        """To perform function _clean_premiums."""
        # TODO: Need to implement this.
        pass


class ProjectPremium(AbstractBaseModel):
    """Model to store premium details of a project. All the type of premiums
    can be handled using the following fields.

    Attributes:
        external_id(str)        : External id of the premium.
        name(str)               : Name of the Premium.
        type(choice)            : What is the premium based on.
                                    - Per transaction
                                    - Per KG
                                    - Per unit currency
                                    - Per farmer
        dependant_on_card(bool) : Whether the premium is dependant on whether
                                  the farmer is producing his NFC card.
        amonut(float)           : Amount of premium.
        included(bool)          : Whether the premium is included in the price
                                  entered by the collector.
        calculation_type        : Calculation type according to the scenarios.

    Examples:
        1) If the premium if a fixed value per transaction, say $10
            - type -> PREMIUM_TYPE_PER_TRANSACTION
            - amount -> 10
        2) If the premium is $1 for every KG purchased
            - type -> PREMIUM_TYPE_PER_KG
            - amount -> 1
        3) If the premium is a one time payment of $50 for a farmer
            - type -> PREMIUM_TYPE_PER_FARMER
            - amount -> 50
        4) If the premium is 20% of the total price paid,
            - type -> PREMIUM_TYPE_PER_UNIT_CURRENCY
            - amount -> 0.2
    """
    external_id = models.CharField(max_length=500, null=True, blank=True)
    category = models.CharField(
        max_length=20,
        choices=PREMIUM_CATEGORY_CHOICES,
        default=TRANSACTION_PREMIUM,
    )
    name = models.CharField(max_length=100, default="", null=True, blank=True)
    owner = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="owned_premiums",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="premiums",
        null=True,
        blank=True,
    )
    type = models.IntegerField(
        default=constants.PREMIUM_TYPE_PER_UNIT_CURRENCY,
        choices=constants.PREMIUM_TYPE_CHOICES,
    )
    amount = models.FloatField(default=None, null=True, blank=True)
    included = models.BooleanField(default=True)
    dependant_on_card = models.BooleanField(default=False)
    applicable_activity = models.IntegerField(
        default=constants.PREMIUM_APPLICABLE_ACTIVITY_BUY,
        choices=constants.PREMIUM_APPLICABLE_ACTIVITY_CHOICES,
    )
    calculation_type = models.CharField(
        max_length=20,
        default=constants.NORMAL,
        choices=constants.CALCULATION_TYPE_CHOICES,
    )
    is_active = models.BooleanField(default=True)

    objects = ProjectPremiumQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} - {self.owner.full_name} | {self.id}"

    def save(self, **kwargs):
        """Save the object.

        This method updates the owner and then calls the superclass`s 'save'
        method to save the object.

        Parameters:
        - kwargs: Additional keyword arguments to pass to the save method.

        Returns:
        - None
        """
        self._update_owner()
        super().save(**kwargs)

    def _update_owner(self):
        """Update owner from project."""
        if not self.owner:
            self.owner = self.project.owner if self.project else None

    @property
    def active_options(self):
        """Return the active options."""
        return self.options.filter(is_active=True)


class PremiumOption(AbstractBaseModel):
    """Represents a premium slab for a project's premium.

    Attributes:
        premium (ForeignKey): The project premium associated with the slab.
        name (str): Name showing in the drop-down.
        amount (float): The amount for the premium slab.
    """

    premium = models.ForeignKey(
        ProjectPremium, on_delete=models.CASCADE, related_name="options"
    )
    name = models.CharField(max_length=25)
    amount = models.FloatField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.premium.name} : {self.name} : {self.amount} | {self.pk}"


class NodeCard(AbstractBaseModel):
    """Model to store cards and to what node it is attached to.

    Attributes:
        external_id(str): External id of the card
        node(obj)       : Node the card is assigned to
        card_id(char)   : hexID of the card
        fairid(char)    : alphanumerical id printed in the node card
    """
    external_id = models.CharField(max_length=500, null=True, blank=True)
    node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.SET_NULL,
        related_name="cards",
        null=True,
        default=None,
        blank=True,
    )
    card_id = models.CharField(max_length=500, unique=True)
    fairid = models.CharField(max_length=500, default="")
    status = models.IntegerField(
        default=constants.CARD_STATUS_ACTIVE,
        choices=constants.CARD_STATUS_CHOICES,
    )
    reference = models.OneToOneField(
        "supply_chains.FarmerReference",
        on_delete=models.CASCADE,
        related_name="farmer_reference",
        null=True,
        blank=True,
    )

    def __str__(self):
        """To perform function __str__."""
        name = self.node.full_name if self.node else "None"
        return f"{self.card_id} - {name} | {self.id}"

    @db_transaction.atomic
    def save(self, **kwargs):
        """To perform function save."""
        self.new_instance = not self.pk
        if self.node_changed():
            self._create_history()
            self.external_id = None
        self.update_or_create_reference()
        super(NodeCard, self).save(**kwargs)

    def _create_history(self):
        """Create a new NodeCardHistory entry for this NodeCard instance.

        If there is a previous NodeCardHistory entry for the same card ID, its
        status will be updated to "REMOVED" if this NodeCard's status is
        "ACTIVE". If the previous status was "REISSUE" or "NEW", and the
        previous node is of type NODE_TYPE_FARM, a new NodeCardHistory entry
        with status "REMOVED" will be created for the previous node.

        If there is a previous NodeCardHistory entry for the same node ID with
        status "REISSUE" or "NEW", and the previous node is of type
        NODE_TYPE_FARM, a new NodeCardHistory entry with status "REMOVED"
        will be created for the previous node, unless the previous
        NodeCardHistory entry has the same ID as the new entry.

        The new NodeCardHistory entry will have the same node ID, card ID,
        creator, updater, created_on, and updated_on values as this NodeCard
        instance.
        """

        # Get last node history against card_id
        last_card = NodeCardHistory.objects.filter(
            card_id=self.card_id
        ).first()

        # Get last node history against node_id
        last_node = NodeCardHistory.objects.filter(
            node_id=self.node_id,
            status__in=[
                constants.CARD_ISSUE_STATUS_REISSUE,
                constants.CARD_ISSUE_STATUS_NEW,
            ],
        ).first()

        data_dict = {
            "node_id": self.node_id,
            "card_id": self.card_id,
            "creator": self.creator,
            "updater": self.updater,
            "updated_on": self.updated_on,
            "created_on": self.created_on,
        }

        if last_card:
            data_dict["status"] = (
                constants.CARD_ISSUE_STATUS_REISSUE
                if self.status == constants.CARD_STATUS_ACTIVE
                else constants.CARD_ISSUE_STATUS_REMOVED
            )
            if (
                last_card.status
                in [
                    constants.CARD_ISSUE_STATUS_REISSUE,
                    constants.CARD_ISSUE_STATUS_NEW,
                ]
                and last_card.node
                and last_card.node.type == NODE_TYPE_FARM
            ):
                last_card.pk = None
                last_card.status = constants.CARD_ISSUE_STATUS_REMOVED
                last_card.save()

        if (
            last_node
            and last_node.node.type == NODE_TYPE_FARM
            and (not last_card or (last_card and last_node.id != last_card.id))
        ):
            last_node.pk = None
            last_node.status = constants.CARD_ISSUE_STATUS_REMOVED
            last_node.save()

        NodeCardHistory.objects.create(**data_dict)

    def update_or_create_reference(self):
        """Create farmer reference entry for NodeCard."""
        new_instance = not self.pk

        # update already available reference.
        old_instance_checks = (not new_instance, self.reference, self.node)
        if all(old_instance_checks) and self.node.type == NODE_TYPE_FARM:
            self.reference.farmer_id = self.node_id
            self.reference.save()

        # create a new reference.
        new_instance_checks = (new_instance, self.node)
        if all(new_instance_checks) and self.node.type == NODE_TYPE_FARM:
            self._create_reference()

    def _create_reference(self):
        name_string = TRACE_FARMER_REFERENCE_NAME
        reference_model = apps.get_model("supply_chains", "Reference")
        farmer_reference_model = apps.get_model(
            "supply_chains", "FarmerReference"
        )

        try:
            ref = reference_model.objects.get(name__iexact=name_string)
        except reference_model.DoesNotExist:
            error_string = (
                f"{name_string} reference is missing from "
                f"reference table. Add reference to assign card."
            )
            raise ValidationError(error_string)
        except reference_model.MultipleObjectsReturned:
            refs = reference_model.objects.filter(name__iexact=name_string)
            ref = refs.last()  # always gets the first one crated.

        # create farmer reference
        self.reference = farmer_reference_model.objects.create(
            reference_id=ref.id,
            farmer_id=self.node_id,
            number=self.fairid or self.card_id,
        )

    def node_changed(self):
        """Check if the node has changed since the last save.

        If this is a new instance, return True. Otherwise, compare the
        current node with the node in the previous instance of this
        object. If they are different, return True. Otherwise, return
        False.
        """
        if not self.node:
            return False
        if self.new_instance:
            return True
        previous_instance = self.__class__.objects.only("node").get(pk=self.pk)
        return previous_instance.node != self.node


class Payment(AbstractBaseModel):
    """Model to store the details about payment earned by nodes.

    Attributes:
        external_id(str)        : External id of the payment.
        source(obj)       : Node that earned the payment
        destination(obj)       : Node that sent the payment
        premium(obj)    : Premium type that was issued
        amount(obj)     : Amount that was issued as part of the premium
        transaction(obj): Transaction along which the premium was issues
    """
    external_id = models.CharField(max_length=500, null=True, blank=True)
    payment_type = models.CharField(
        max_length=20,
        choices=constants.PAYMENT_TYPE_CHOICES,
        default=constants.BASE_TRANSACTION,
    )
    source = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="to_payments",
        null=True,
        blank=True,
    )
    destination = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="from_payments",
        null=True,
        blank=True,
    )
    premium = models.ForeignKey(
        ProjectPremium,
        on_delete=models.PROTECT,
        related_name="premium_payments",
        null=True,
        blank=True,
    )
    card = models.ForeignKey(
        NodeCard, on_delete=models.CASCADE, null=True, blank=True
    )
    invoice = models.FileField(
        upload_to=library._get_file_path, null=True, blank=True
    )
    invoice_number = models.CharField(max_length=100, null=True, blank=True)
    amount = models.FloatField(default=0.0)
    selected_option = models.ForeignKey(
        PremiumOption, on_delete=models.SET_NULL, null=True, blank=True
    )
    currency = models.CharField(
        choices=CURRENCY_CHOICES, null=True, blank=True, max_length=5
    )
    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.CASCADE,
        related_name="transaction_payments",
        null=True,
        blank=True,
    )
    verification_latitude = models.FloatField(default=0.0)
    verification_longitude = models.FloatField(default=0.0)

    method = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        choices=constants.VERIFICATION_METHOD_CHOICES,
    )
    description = models.TextField(null=True, blank=True)
    extra_fields = JSONField(blank=True, null=True)

    objects = PaymentQuerySet.as_manager()

    def __str__(self):
        show_str = (
            self.premium.name
            if self.premium
            else f"Transaction {self.transaction.number}"
        )
        return f"{show_str} | {self.pk}"

    def save(self, **kwargs):
        """save() override to pre and post save functions."""
        self._update_from_transaction()
        self._update_payment_status()
        self._update_verification_method()
        self._update_description()
        super().save(**kwargs)

    def _update_from_transaction(self):
        """To update payment_from and payment_to from the available
        transaction."""
        if self.transaction:
            self.source = self.transaction.destination
            self.destination = self.transaction.source

            # invoice will get from transaction if not available.
            if not self.invoice:
                self.invoice = self.transaction.invoice
            self.card = self.transaction.card
            self.invoice_number = self.transaction.invoice_number

            ext_transaction = self.transaction.externaltransaction
            if ext_transaction:
                self.currency = ext_transaction.currency

                # getting verification lat-long
                lat = ext_transaction.verification_latitude
                lon = ext_transaction.verification_longitude
                self.verification_latitude = lat
                self.verification_longitude = lon

                # Updating meta
                self.created_on = ext_transaction.created_on
                self.updated_on = ext_transaction.updated_on
                self.creator = ext_transaction.creator
                self.updater = ext_transaction.updater

    def _update_payment_status(self):
        """To update payment_status with available relations."""
        if self.transaction and self.premium:
            self.payment_type = constants.TRANSACTION_PREMIUM
        else:
            if self.transaction:
                self.payment_type = constants.BASE_TRANSACTION
            elif self.premium:
                self.payment_type = constants.BASE_PREMIUM
            else:
                raise Exception("Payment type can not determined.")

    def _update_verification_method(self):
        """Update verification method card/receipt."""
        if self.card:
            self.method = constants.CARD_VERIFICATION
        elif self.invoice:
            self.method = constants.INVOICE_VERIFICATION
        else:
            self.method = constants.NO_VERIFICATION

    def _update_description(self):
        """To update description with auto generated text."""
        if not self.description:
            payment_str = self.premium.name if self.premium else "Base price"
            self.description = (
                f" {self.source.full_name} paid "
                f"{payment_str} to "
                f"{self.destination.full_name}"
            )
            if self.transaction and self.transaction.product:
                self.description += (
                    f" for product " f"{self.transaction.product.name}"
                )


class NodeCardHistory(AbstractBaseModel):
    """History model to store Node Card logs."""

    node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.SET_NULL,
        related_name="card_history",
        null=True,
        default=None,
        blank=True,
    )
    card_id = models.CharField(max_length=500)
    status = models.IntegerField(
        default=constants.CARD_ISSUE_STATUS_NEW,
        choices=constants.CARD_ISSUE_STATUS_CHOICES,
    )

    def __str__(self):
        """To perform function __str__."""
        status = dict(constants.CARD_ISSUE_STATUS_CHOICES)[self.status]
        return f"{self.card_id} - {status} | {self.pk}"

    def save(self, **kwargs):
        """Saves the model instance to the database.

        This method overrides the default save method of the model. It first
        checks whether the instance is a new instance or an existing one. If
        it's a new instance, it sets the `new_instance` attribute to True.
        Then, it saves the instance to the database using the parent class's
        'save' method. Finally, it calls the `log_activity` method to log any
        relevant activity related to the instance.

        Parameters:
        - *args: Variable-length argument list.
        - **kwargs: Arbitrary keyword arguments.
        """
        super().save(**kwargs)
        self.log_activity()

    def log_activity(self):
        """Logs an activity based on the status of the node card history.

        If the status is `CARD_ISSUE_STATUS_REMOVED`, an activity is
        logged with the type `CARD_REMOVED` and the creator of the card.
        Otherwise, an activity is logged with the type `CARD_ADDED` and
        the updater of the card.
        """
        if self.status == constants.CARD_ISSUE_STATUS_REMOVED:
            Activity.log(
                user=self.creator,
                event=self,
                activity_type=act_constants.CARD_REMOVED,
                object_id=self.pk,
                object_type=act_constants.OBJECT_TYPE_NODE_CARD_HISTORY,
                node=self.node,
            )
        else:
            Activity.log(
                user=self.updater,
                event=self,
                activity_type=act_constants.CARD_ADDED,
                object_id=self.pk,
                object_type=act_constants.OBJECT_TYPE_NODE_CARD_HISTORY,
                node=self.node,
            )
