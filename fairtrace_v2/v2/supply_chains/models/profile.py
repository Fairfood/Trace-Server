import os
from collections import defaultdict
from datetime import date
from datetime import timedelta

from babel.numbers import format_decimal
from common.library import _decrypt
from common.library import _encrypt
from common.library import _get_file_path
from common.library import _percentage
from common.models import AbstractBaseModel
from common.models import Address
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction as db_transaction
from django.db.models import Q
from django.db.models import Sum
from django.utils.translation import gettext as _
from django_extensions.db.fields.json import JSONField
from sentry_sdk import capture_exception
from v2.accounts.constants import VTOKEN_TYPE_INVITE
from v2.accounts.models import AbstractPerson
from v2.accounts.models import Person
from v2.accounts.models import ValidationToken
from v2.activity import constants as act_constants
from v2.activity.models import Activity
from v2.blockchain.constants import HBAR_RECHARGE_AMOUNT
from v2.blockchain.models.create_account import AbstractHederaAccount
from v2.blockchain.models.ghost import TreasuryWallet
from v2.blockchain.models.transfer_hbar import AbstractHBARTransaction
from v2.communications import constants as notif_constants
from v2.communications.models import Notification
from v2.supply_chains import constants
from v2.transactions import constants as trans_constants
from v2.transactions.models import ExternalTransaction

from ...projects.constants import BASE_PREMIUM
from ...projects.constants import BASE_TRANSACTION
from ...projects.constants import TRANSACTION_PREMIUM
from ...projects.models import Payment
from ..constants import APPROXIMATE
from ..constants import CONSENT_STATUS_TYPES
from ..constants import GRANTED
from ..constants import LOCATION_TYPES
from ..managers import FarmerAttachmentQuerySet
from ..managers import FarmerPlotQuerySet
from ..managers import FarmerReferenceQuerySet
from ..managers import ReferenceQuerySet
from .node import Node
from .supply_chain import SupplyChain


# Create your models here.


class BlockchainWallet(AbstractBaseModel, AbstractHederaAccount):
    """Blockchain Account Model.

    Attributes:
        public(str): Blockchain account key
        private(str): Blockchain account private
    """

    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="wallets",
        null=True,
        blank=True,
        default=None,
    )
    account_id = models.CharField(
        max_length=50, null=True, blank=True, default=""
    )
    public = models.CharField(
        max_length=2000, default="", null=True, blank=True
    )
    private = models.CharField(
        max_length=2000, default="", null=True, blank=True
    )

    wallet_type = models.IntegerField(
        default=constants.BLOCKCHAIN_WALLET_TYPE_HEDERA,
        choices=constants.BLOCKCHAIN_WALLET_TYPES,
    )
    default = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        if "private" in kwargs:
            raise ValueError(
                "Secret cannot be set when creating object. Use .set_private()"
            )
        super(BlockchainWallet, self).__init__(*args, **kwargs)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.public} | {self.id}"

    @property
    def explorer_url(self):
        """To perform function xplorer_url."""
        if self.wallet_type == constants.BLOCKCHAIN_WALLET_TYPE_HEDERA:
            return settings.HEDERA_ACCOUNT_EXPLORER.format(
                account_id=self.account_id
            )
        return ""

    def disable(self):
        """To perform function isable."""
        self.default = False
        self.save()
        if self.block_chain_request:
            self.block_chain_request.discard()
        return True

    def topup_hbar(self, force=False):
        """To perform function topup_hbar."""
        today = date.today()
        today - timedelta(days=7)
        if self.node.is_test:
            return False
        topup = WalletTopUp.objects.create(
            node_wallet=self, amount=HBAR_RECHARGE_AMOUNT
        )
        topup.recharge()
        return True

    def set_private(self, raw_private):
        """To perform function set_private."""
        self.private = _encrypt(raw_private)
        self.save()
        return True

    @property
    def decrypted_private(self):
        """Decrypted private data."""
        return _decrypt(self.private)

    def pre_check(self):
        """Pre-check."""
        success, message = super(BlockchainWallet, self).pre_check()
        if not success:
            return success, message
        if self.private or self.public:
            return False, "Blockchain account has already been set-up"
        return True, "Pre-check success"

    def create_blockchain_account(self, user=None):
        """Create block-chain account."""
        success, message = self.pre_check()
        if not success:
            print(f"{self.__class__.__name__} - {self.id} | {message}")
            return False
        try:
            self.initialize(user)
            self.block_chain_request.send()
            return True
        except Exception as e:
            capture_exception(e)
            return False

    def update_hedera_data(self, bc_data):
        """Update blockchain information."""
        self.account_id = bc_data["accountID"]
        self.public = bc_data["accountPublic"]
        self.save()
        self.set_private(bc_data["accountPrivate"])

        self.post_success()
        return True

    def post_success(self):
        """Update blockchain information on node table."""
        node = self.node
        node.blockchain_address = self.public
        node.save()

        # Associate all remaining tokens in the supplychain to the new wallet
        for sc in self.node.supply_chains.all():
            from v2.supply_chains.models import WalletTokenAssociation

            WalletTokenAssociation.create_association(
                wallet=self, supply_chain=sc
            )

        # Migrate existing batches to new wallet
        for batch in (
            self.node.batches.all()
            .exclude(node_wallet=self, current_quantity__gt=0)
            .exclude(node_wallet=None, current_quantity__gt=0)
        ):
            batch.migrate_balance_asset()

        # Update cache and relog pending transactions
        self.node.update_cache()
        self.node.retry_pending_blockchain_actions()
        return True


class WalletTopUp(AbstractBaseModel, AbstractHBARTransaction):
    """Model to store HBAR recharge transactions.

    Attributes:
        node_wallet(obj)        : Wallet that is recharges.
        amount(decimal)         : Amount that is recharged.
        blockchain_id(str)      : transaction id
        blockchain_address(str) : transaction hash
    """

    node_wallet = models.ForeignKey(
        BlockchainWallet, on_delete=models.CASCADE, related_name="recharges"
    )
    amount = models.DecimalField(default=0.0, max_digits=5, decimal_places=3)
    blockchain_id = models.CharField(default="", max_length=500)
    blockchain_address = models.CharField(default="", max_length=500)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.node_wallet.public} - {self.amount} | {self.id}"

    @classmethod
    def new_recharge(cls, account_id):
        """New recharge."""
        wallet = BlockchainWallet.objects.get(accunt_id=account_id)
        if not wallet.wallet_type == constants.BLOCKCHAIN_WALLET_TYPE_HEDERA:
            print("Can only recharge hedera wallets")
            return False
        topup = cls.objects.create(
            node_wallet=wallet, amount=HBAR_RECHARGE_AMOUNT
        )
        topup.recharge()
        return True

    @property
    def recharge_amount(self):
        """Recharge amount."""
        return self.amount

    @property
    def initiator_wallet(self):
        """The initiator is the project itself."""
        return TreasuryWallet()

    @property
    def receiver_id(self):
        """Receiver ID."""
        return self.node_wallet.account_id

    def pre_check(self):
        """Pre-check."""
        success, message = super(WalletTopUp, self).pre_check()
        if not success:
            return success, message
        if (
            self.node_wallet.wallet_type
            != constants.BLOCKCHAIN_WALLET_TYPE_HEDERA
        ):
            return False, "Can only recharge hedera wallets"
        if not self.node_wallet.account_id:
            self.node_wallet.create_blockchain_account()
            return False, "Node wallet not setup"
        return True, "Pre-check success"

    def recharge(self):
        """Recharge."""
        success, message = self.pre_check()
        if not success:
            print(f"{self.__class__.__name__} - {self.id} | {message}")
            return False
        try:
            self.initialize(self.creator)
            self.block_chain_request.send()
            return True
        except Exception as e:
            capture_exception(e)
            return False

    def update_hedera_data(self, bc_data):
        """Update Hedera data."""
        self.blockchain_id = bc_data["transactionId"]
        self.blockchain_address = bc_data["transactionHash"]
        self.save()
        self.post_success()
        return True

    def post_success(self):
        """Post success."""
        for req in self.node_wallet.deferred_requests.all():
            req.retry()
            self.node_wallet.deferred_requests.remove(req)
        return True


class Operation(AbstractBaseModel):
    """Available operations for a Node.

    Attributes:
        node_type(int[choice])  : Type of the Node (Company of Farmer)
        name(str)               : Operation name
        image(image)            : Default image for the operation
        supply_chains(obj)      : Supply chains that the operations is a part
                                    of.
    """

    node_type = models.IntegerField(choices=constants.NODE_TYPE_CHOICES)
    name = models.CharField(max_length=100)
    image = models.FileField(upload_to=_get_file_path, blank=True)
    supply_chains = models.ManyToManyField(
        SupplyChain,
        through="supply_chains.OperationSupplyChain",
        related_name="operations",
    )

    def __str__(self):
        """To perform function __str__."""
        return "%s : %s" % (self.node_type, self.name)


class OperationSupplyChain(AbstractBaseModel):
    """Model to make operations/roles supply chain specific. Used as a through
    model for supply_chains field in Operation model.

    Attributes:
        operation(obj)      : Operation object that is part of the supply chain
        supply_chain(obj)   : Supply chains which the operation is a part of.
        active(bool)        : Whether the role is active now.
    """

    operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        related_name="supply_chain_objects",
    )
    supply_chain = models.ForeignKey(
        SupplyChain, on_delete=models.CASCADE, related_name="operation_objects"
    )
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("supply_chain", "operation")

    def __str__(self):
        """To perform function __str__."""
        return f"{self.operation.name} - {self.supply_chain.name} | {self.id}"


class Farmer(Node, AbstractPerson):
    """Farmer Model, Inherited from Node model."""

    family_members = models.IntegerField(null=True, blank=True, default=1)
    farm_area = models.CharField(
        max_length=50, default="", blank=True, null=True
    )
    income_from_main_product = models.FloatField(default=0.0, null=True,
                                                 blank=True)
    income_from_other_sources = models.CharField(
        max_length=500, default="", blank=True, null=True
    )
    main_product = models.CharField(
        max_length=100, default="", null=True, blank=True
    )
    extra_fields = JSONField(blank=True, null=True)
    consent_status = models.CharField(
        max_length=20, choices=CONSENT_STATUS_TYPES, default=GRANTED
    )

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        kwargs["type"] = constants.NODE_TYPE_FARM
        super(Farmer, self).__init__(*args, **kwargs)

    def clean(self):
        """Cleans and validates the farmer's data.

        This method is automatically called by Django during model validation.

        It ensures that the first name and last name are properly formatted by
        capitalizing the first letter of each name.
        """
        super(Farmer, self).clean()
        if self.first_name:
            self.first_name = str(self.first_name).title()
        if self.last_name:
            self.last_name = str(self.last_name).title()

    def save(self, *args, **kwargs):
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
        self.new_instance = not self.pk
        super().save(*args, **kwargs)
        self.log_activity()
        self.create_identification_ref()

    def __str__(self):
        """To perform function __str__."""
        return "%s %s - %d" % (self.first_name, self.last_name, self.id)

    def log_activity(self):
        """Logs an activity based on whether the object is being created or
        updated.

        If the object is being created, logs an activity with the creator as
        the user and the creation event as the activity type. If the object is
        being updated, logs an activity with the updater as the user and the
        edit event as the activity type.

        The logged activity includes information about the object being created
         or updated, such as the object ID, object type, and node.

        Returns:
            None
        """
        if self.new_instance:
            Activity.log(
                user=self.creator,
                event=self,
                activity_type=act_constants.FARMER_CREATED,
                object_id=self.pk,
                object_type=act_constants.OBJECT_TYPE_NODE,
                node=self,
            )
        else:
            Activity.log(
                user=self.updater,
                event=self,
                activity_type=act_constants.FARMER_EDITED,
                object_id=self.pk,
                object_type=act_constants.OBJECT_TYPE_NODE,
                node=self,
            )

    def create_identification_ref(self):
        """Create an identification reference for the current instance.

        This function checks if an identification reference needs to be
        created based on the instance state and conditions. If a reference
        needs to be created, it retrieves the latest 'Co-Operative ID'
        reference and creates a farmer reference using the instance's
        identification number.

        Note: The 'Co-Operative ID' reference must exist in the
            'Reference' model.
        """
        if not self.identification_no:
            return

        update_reference = self.new_instance or (
            self.__class__.objects.filter(
                identification_no__isnull=True, pk=self.pk
            ).exists()
        )

        if update_reference:
            reference_model = apps.get_model("supply_chains", "Reference")
            ref = reference_model.objects.filter(name="Co-Operative ID").last()

            if ref:
                # noinspection PyUnresolvedReferences
                self.farmerreference_set.create(
                    farmer_id=self.pk,
                    reference_id=ref.pk,
                    number=self.identification_no,
                )

    @property
    def name(self):
        """Returns name."""
        return "%s %s" % (self.first_name, self.last_name)

    @property
    def short_name(self):
        """Returns short_name."""
        return f"{self.first_name} {self.last_name[:1]}".title()

    @property
    def node_object(self):
        """The connected node object."""
        return self

    @property
    def total_area_in_use(self):
        """Returns the total area in use by the farmer.

        The total area in use is calculated as the sum of the total plot areas
        of all the farmer's plots.

        Returns:
        - Decimal: The total area in use by the farmer.
        """
        # noinspection PyUnresolvedReferences
        return self.plots.aggregate(
            total_plot_area_sum=Sum("total_plot_area")
        )["total_plot_area_sum"]

    @property
    def all_crop_types(self):
        """Returns a string of all the crop types grown by the farmer.

        The crop types are obtained from all the farmer's plots.

        Returns:
        - str: A string of all the crop types grown by the farmer.
        """
        # noinspection PyUnresolvedReferences
        crop_types = [
            crop_type
            for crop_type in self.plots.values_list("crop_types", flat=True)
            if crop_type
        ]
        return ", ".join(crop_types)

    @property
    def total_income(self):
        """Calculates the total income earned by the farmer.

        The total income is calculated as follows:
        - For each currency used in payments, the total amount and amount
            earned from products and premiums are calculated.
        - The results are returned in a dictionary, where each key is the name
            of a field and each value is a list of dictionaries containing the
            amount and currency for that field and currency.

        Returns:
        - dict: A dictionary containing the total amount earned and amounts
            earned from products and premiums for each currency used in
            payments.
        """
        # noinspection PyUnresolvedReferences
        available_currencies = self.from_payments.values_list(
            "currency", flat=True
        )
        data = defaultdict(list)
        for currency in available_currencies:
            payments = self.from_payments.filter(currency=currency)

            # get total_amount from payments
            total_amount = (
                payments.aggregate(total_amount=Sum("amount"))["total_amount"]
                or 0
            )
            data["total_amount"].append(
                {"amount": round(total_amount), "currency": currency}
            )

            # get transaction base price from payments.
            amount_from_products = (
                payments.filter(payment_type=BASE_TRANSACTION).aggregate(
                    total_amount=Sum("amount")
                )["total_amount"]
                or 0
            )
            data["amount_from_products"].append(
                {"amount": round(amount_from_products), "currency": currency}
            )

            # get premium price from payments.
            amount_from_premiums = (
                payments.filter(
                    payment_type__in=[BASE_PREMIUM, TRANSACTION_PREMIUM]
                ).aggregate(total_amount=Sum("amount"))["total_amount"]
                or 0
            )
            data["amount_from_premiums"].append(
                {"amount": round(amount_from_premiums), "currency": currency}
            )
        return data

    @property
    def profile_completion(self):
        """To perform function profile_completion."""
        total = 0
        filled = 0
        for field in constants.FARMER_PROFILE_FIELDS:
            if type(field) == str:
                value = getattr(self, field)
                total += 1
                if value:
                    filled += 1
            elif type(field == dict):
                for fk, sub_keys in field.items():
                    if not getattr(self, fk, None):
                        total += len(sub_keys)
                        continue
                    for sub_key in sub_keys:
                        value = getattr(getattr(self, fk), sub_key)
                        total += 1
                        if value:
                            filled += 1
        return int(_percentage(filled, total))

    def _numeric_to_language_format(self, language, data):
        """To perform function _numeric_to_language_format."""
        data["volume"] = format_decimal(data["volume"], locale=language)
        data["income"] = format_decimal(data["income"], locale=language)
        data["premium"] = format_decimal(data["premium"], locale=language)
        return True

    def transaction_count(self, language):
        """To perform function transaction_count."""
        data = {"volume": 0, "income": 0, "premium": 0}
        external_transactions = ExternalTransaction.objects.filter(
            Q(source=self) | Q(destination=self)
        )
        data["count"] = external_transactions.count()
        for external_transaction in external_transactions:
            data["volume"] += float(external_transaction._destination_quantity)
        for external_transaction in external_transactions.filter(
            type=trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
        ):
            data["income"] += external_transaction.price
        for premium_earned in Payment.objects.filter(destination=self):
            data["premium"] += premium_earned.amount
        self._numeric_to_language_format(language, data)
        return data


class Company(Node):
    """Company Model, Inherited from Node.

    Attributes:
        name: Company Name
        incharge: Details of the person in charge
        make_farmers_private: If true, farmers and transactions will not be
            visible to other
    """

    role = models.IntegerField(
        choices=constants.COMPANY_ROLE_CHOICES,
        default=constants.COMPANY_ROLE_ACTOR,
    )
    name = models.CharField(max_length=500, unique=True)
    incharge = models.ForeignKey(
        Person, null=True, on_delete=models.SET_NULL, blank=True
    )
    make_farmers_private = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        kwargs["type"] = constants.NODE_TYPE_COMPANY
        super(Company, self).__init__(*args, **kwargs)

    def __str__(self):
        """To perform function __str__."""
        return "%s - %d" % (self.name, self.id)

    def clean(self):
        """Cleans and validates the company's data.

        This method is automatically called by Django during model validation.

        It ensures that the company name is properly formatted by capitalizing
        the first letter of the name.
        """
        super(Company, self).clean()
        if self.name:
            self.name = str(self.name).title()

    @property
    def short_name(self):
        """To perform function short_name."""
        return self.name

    @property
    def node_object(self):
        """To perform function node_object."""
        return self

    @property
    def profile_completion(self):
        """For completing the profile."""
        total = 0
        filled = 0
        for field in constants.COMPANY_PROFILE_FIELDS:
            if type(field) == str:
                value = getattr(self, field)
                total += 1
                if value:
                    filled += 1
            elif type(field == dict):
                for fk, sub_keys in field.items():
                    if not getattr(self, fk, None):
                        total += len(sub_keys)
                        continue
                    for sub_key in sub_keys:
                        value = getattr(getattr(self, fk), sub_key)
                        total += 1
                        if value:
                            filled += 1
        return int(_percentage(filled, total))


class NodeManager(AbstractBaseModel):
    """Model to store the managers of a node."""

    node = models.ForeignKey(
        Node,
        null=True,
        on_delete=models.CASCADE,
        related_name="node_manager_objects",
    )
    manager = models.ForeignKey(
        Node,
        null=True,
        on_delete=models.CASCADE,
        related_name="managed_node_objects",
    )

    def __str__(self):
        """To perform function __str__."""
        return "%s manages %s | %d" % (
            self.manager.full_name,
            self.node.full_name,
            self.id,
        )

    def save(self, *args, **kwargs):
        """Overriding save()."""
        super(NodeManager, self).save(*args, **kwargs)
        db_transaction.on_commit(
            lambda: self.node.create_or_update_graph_node()
        )


class NodeDocument(AbstractBaseModel):
    """To store documents added by a Node.

    Attributes:
        node (obj): Foreign key to the Node that owns the file.
        file (file): File uploaded.
        name (str): Name mentioned
        type (choice): Type of document. Note mentioned in the initial
        requirments, Therefore set to default for now.
    """

    node = models.ForeignKey(
        Node, null=True, on_delete=models.CASCADE, related_name="documents"
    )
    name = models.CharField(max_length=500, default="", blank=True)
    file = models.FileField(
        upload_to=_get_file_path, null=True, default=None, blank=True
    )
    type = models.IntegerField(
        choices=constants.DOCUMENT_TYPE_CHOICES,
        default=constants.DOCUMENT_TYPE_DEFAULT,
    )

    def __str__(self):
        """To perform function __str__."""
        return "%s by %s - %d" % (self.name, self.node.full_name, self.id)

    def log_activity(self):
        """Logging activity."""
        Activity.log(
            event=self,
            activity_type=act_constants.ADDED_NODE_DOCUMENT,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_NODE_DOCUMENT,
            user=self.creator,
            node=self.node,
        )

    def log_delete_activity(self, user):
        """Log delete activity."""
        context = {"file_name": self.name, "member_name": user.name}
        Activity.log(
            event=self.node,
            activity_type=act_constants.DELETED_NODE_DOCUMENT,
            object_id=self.node.id,
            object_type=act_constants.OBJECT_TYPE_NODE,
            user=user,
            node=self.node,
            context=context,
        )


class NodeMember(AbstractBaseModel):
    """To store members of each nodes.

    Attributes:
        node (obj): Foreign key to the node
        user (obj): Foreign key to the fairfood user.
        type (obj): Type of member. Value from NODE_MEMBER_CHOICES can be,
            - NODE_MEMBER_TYPE_ADMIN - Can manage other members
            - NODE_MEMBER_TYPE_MEMBER - Can add connections perform
            transactions.
            - NODE_MEMBER_TYPE_VIEWER - Has read permission across the
                                        dashboard.
    """

    node = models.ForeignKey(
        Node, null=True, on_delete=models.CASCADE, related_name="nodemembers"
    )
    user = models.ForeignKey(
        "accounts.FairfoodUser",
        on_delete=models.CASCADE,
        related_name="usernodes",
    )
    type = models.IntegerField(
        default=constants.NODE_MEMBER_TYPE_MEMBER,
        choices=constants.NODE_MEMBER_TYPE_CHOICES,
    )
    active = models.BooleanField(default=False)
    vtoken = models.OneToOneField(
        "accounts.ValidationToken",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    available_languages = models.CharField(max_length=500, default="en")

    class Meta:
        unique_together = ["node", "user"]

    def __str__(self):
        """To perform function __str__."""
        return "%s - %s | %d" % (self.node.full_name, self.user.name, self.id)

    @property
    def get_lower_type_display_name(self):
        """Lower type display name."""
        return self.get_type_display().lower()

    @db_transaction.atomic
    def delete(self, user, using=None, keep_parents=False):
        """Override delete()."""
        self.hide_notifications()
        self.log_removed_activity(user)
        if self.user.default_node == self.node:
            user = self.user
            user.default_node = None
            user.save()
        return super(NodeMember, self).delete(using, keep_parents)

    def make_admin(self, current_user=None):
        """Log for admin."""
        self.type = constants.NODE_MEMBER_TYPE_ADMIN
        self.save()
        if current_user:
            self.updater = current_user
            self.save()
        Activity.log(
            event=self,
            activity_type=act_constants.USER_MADE_ADMIN,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_NODE_MEMBER,
            user=self.user,
            node=self.node,
            prevent_duplication=False,
        )

    def make_member(self, current_user=None):
        """log for a member."""
        self.type = constants.NODE_MEMBER_TYPE_MEMBER
        self.save()
        if current_user:
            self.updater = current_user
            self.save()
        Activity.log(
            event=self,
            activity_type=act_constants.USER_MADE_MEMBER,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_NODE_MEMBER,
            user=self.user,
            node=self.node,
            prevent_duplication=False,
        )

    def send_invite(self, sender=None):
        """Send Invited as member email."""
        if self.user.password:
            token = None
        elif self.vtoken:
            self.vtoken.refresh()
            token = self.vtoken
        else:
            validation = ValidationToken.initialize(
                user=self.user, creator=self.creator, type=VTOKEN_TYPE_INVITE
            )
            self.vtoken = validation
            self.save()
            token = self.vtoken

        notification = Notification.notify(
            token=token,
            event=self,
            user=self.user,
            supply_chain=None,
            actor_node=self.node,
            target_node=self.node,
            notif_type=notif_constants.NOTIF_TYPE_MEMBER_INVITE,
            sender=sender,
        )
        return notification

    def make_viewer(self, current_user=None):
        """Log for a viewer."""
        self.type = constants.NODE_MEMBER_TYPE_VIEWER
        self.save()
        if current_user:
            self.updater = current_user
            self.save()
        Activity.log(
            event=self,
            activity_type=act_constants.USER_MADE_VIEWER,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_NODE_MEMBER,
            user=self.user,
            node=self.node,
            prevent_duplication=False,
        )

    def hide_notifications(self):
        """To hide notification."""
        Notification.objects.filter(
            target_node=self.node, user=self.user
        ).update(visibility=False)

    def unhide_notifications(self):
        """To update notification."""
        Notification.objects.filter(
            target_node=self.node, user=self.user
        ).update(visibility=True)

    def log_added_activity(self):
        """log added activity."""
        Activity.log(
            event=self,
            activity_type=act_constants.ADDED_AS_MEMBER,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_NODE_MEMBER,
            user=self.user,
            node=self.node,
            prevent_duplication=False,
        )

    def log_removed_activity(self, user):
        """Log removed activity."""
        Activity.log(
            event=self,
            activity_type=act_constants.REMOVED_MEMBER,
            object_id=self.node.id,
            object_type=act_constants.OBJECT_TYPE_NODE,
            user=self.user,
            node=self.node,
            prevent_duplication=False,
            context={"user_name": user.name},
        )

    def clean(self):
        """clean data."""
        self._clean_available_languages()

    def _clean_available_languages(self):
        """Validating the available_languages field before saving.

        Checking the languages available in the settings.
        """
        available_language_set = set(
            f"{self.available_languages}".strip("[]")
            .replace(" ", "")
            .split(",")
        )
        ci_language_set = set(dict(settings.LANGUAGES).keys())
        if not available_language_set.issubset(ci_language_set):
            error = _("Language(s) not defined in the system")
            raise ValidationError(f"{error}")
        if "en" not in available_language_set:
            available_language_set.add("en")
        self.available_languages = ",".join(available_language_set)


class Verifier(AbstractBaseModel):
    """Companies that are assigned to a SupplyChain as verifiers."""

    node = models.ForeignKey(
        Node,
        null=True,
        on_delete=models.CASCADE,
        related_name="verifier_sc_objects",
    )
    supply_chain = models.ForeignKey(
        SupplyChain,
        on_delete=models.CASCADE,
        related_name="sc_verifier_objects",
    )
    active = models.BooleanField(default=True)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.node.full_name} {self.supply_chain.name} - {self.id}"


class NodeFeatures(AbstractBaseModel):
    """Features that a node is subscribed to."""

    node = models.OneToOneField(
        Node, null=True, on_delete=models.CASCADE, related_name="features"
    )
    dashboard_theming = models.BooleanField(default=False)
    consumer_interface_theming = models.BooleanField(default=False)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.node.full_name} features - {self.id}"


class Reference(AbstractBaseModel):
    """Identity/Certification provided by different sources.

    * name: a character field that represents the name of the reference.
    * image: an image field that represents the image of the reference. It
        is optional and can be null or blank.
    * description: a text field that provides a description of the
        reference. It is optional and can be null or blank.
    * is_editable: a boolean field that indicates whether the reference is
        editable or not. It is set to True by default.
    """

    name = models.CharField(max_length=250)
    image = models.ImageField(upload_to=_get_file_path, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_editable = models.BooleanField(default=True)

    objects = ReferenceQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} - {self.pk}"


class FarmerReference(AbstractBaseModel):
    """Map reference against farmers.

    * number: A character field that stores the reference number for the
        mapping between the reference and the farmer.
    * reference: A foreign key that references the Reference model. It
        represents the reference associated with the farmer.
    * farmer: A foreign key that references the Farmer model. It represents the
        farmer associated with the reference.
    * source: A foreign key that references the Company model. It represents
        the source of the reference and is optional.
    """

    number = models.CharField(max_length=100)
    reference = models.ForeignKey(Reference, on_delete=models.CASCADE)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE)
    source = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True
    )

    objects = FarmerReferenceQuerySet.as_manager()

    def __str__(self):
        return f"{self.reference.name} {self.farmer.full_name} - {self.pk}"


class FarmerPlot(AbstractBaseModel, Address):
    """A model that represents a plot of land owned by a farmer.

    Attributes:
    - name (str): The name of the plot.
    - farmer (Farmer): The farmer who owns the plot.
    - location_type (str): The type of location for the plot,
        such as "exact" or "approximate".
    - total_plot_area (Decimal): The total area of the plot in square
        meters.
    - crop_types (str): The types of crops grown on the plot.
    """

    name = models.CharField(max_length=20)
    farmer = models.ForeignKey(
        Farmer, on_delete=models.CASCADE, related_name="plots"
    )
    location_type = models.CharField(
        max_length=20, choices=LOCATION_TYPES, default=APPROXIMATE
    )
    total_plot_area = models.DecimalField(
        default=0, max_digits=10, decimal_places=4
    )
    crop_types = models.TextField(null=True, blank=True)

    objects = FarmerPlotQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} {self.farmer.full_name} - {self.pk}"


class FarmerAttachment(AbstractBaseModel):
    """A model that represents a file attachment associated with a farmer.

    Attributes:
    - farmer (Farmer): The farmer associated with the attachment.
    - attachment (FileField): The file attached to the farmer.
    - node (Node): The supply chain node associated with the attachment.
    - name (str): The name of the attachment.
    """

    farmer = models.ForeignKey(
        Farmer, on_delete=models.CASCADE, related_name="attachments"
    )
    attachment = models.FileField(
        upload_to=_get_file_path, blank=True, null=True
    )
    node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="farmer_attachments",
    )
    name = models.CharField(max_length=60)

    objects = FarmerAttachmentQuerySet.as_manager()

    def __str__(self):
        file_name = os.path.basename(self.attachment.name)
        return f"{self.farmer.full_name} : {file_name} - {self.pk}"
