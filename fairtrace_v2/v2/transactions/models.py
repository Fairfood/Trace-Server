"""Models for transactions."""
import json
import os

from common import library as comm_lib
from common.currencies import CURRENCY_CHOICES
from common.library import _get_file_path
from common.models import AbstractBaseModel
from common.models import GraphModel
from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django_extensions.db.fields.json import JSONField
from sentry_sdk import capture_exception
from sentry_sdk import capture_message
from v2.activity import constants as act_constants
from v2.activity.models import Activity
from v2.blockchain.models.burn_token import AbstractBurnedToken
from v2.blockchain.models.submit_message import AbstractConsensusMessage
from v2.blockchain.models.transfer_token import AbstractTokenTransaction
from v2.claims import constants as claims_constants
from v2.claims.models import AttachedBatchClaim
from v2.communications.models import Notification
from v2.products import constants as product_constants
from v2.products.models import Product
from v2.supply_chains import constants as sc_constants

from . import constants
from ..projects.constants import TRANSACTION_PREMIUM
from ..projects.models import Payment
from .managers import ExternalTransactionQuerySet
from .managers import InternalTransactionQuerySet
from .managers import TransactionAttachmentQuerySet
from .notification_data import get_notification_data


# Create your models here.


class Transaction(AbstractBaseModel, GraphModel):
    """
    Base Model for all transactions
    Attributes:
        parents(objs)           : Manytomany fields to map the parent
                                  transactions and thereby the graph of all
                                  transactions.
        date(date)              : The date on which the physical transaction
                                  took place, outside the platform
        result_batch(obj)       : The batch that was created after the
                                    transaction.
        deleted(bool)           : Flag to be set if for some reason a
                                  transaction needs to be deleted. The
                                  transaction object will not be deleted,
                                  instead this flag will be set to True.
        blockchain_address(char)  : The hash ID generated after logging the
                                  transaction in blockchain
        transaction_type(int)   : Type of transaction (External/Internal)
        status(int)             : Status of transaction. choice from T
                                  RANSACTION_STATUS_CHOICES
        source_batches(objs)    : Batches from which the transaction was
                                  created. Automatically created when creating,
                                  SourceBatch
    """

    parents = models.ManyToManyField(
        "self", related_name="children", symmetrical=False, blank=True
    )

    number = models.IntegerField(default=0)
    date = models.DateTimeField(default=timezone.now)
    invoice_number = models.CharField(max_length=100, default="", blank=True)
    invoice = models.FileField(
        upload_to=comm_lib._get_file_path, null=True, default=None, blank=True
    )
    comment = models.CharField(max_length=1000, default="", blank=True)
    card = models.ForeignKey(
        "projects.NodeCard", null=True, blank=True, on_delete=models.SET_NULL
    )
    quality_correction = models.FloatField(default=100.00)

    blockchain_id = models.CharField(default="", max_length=500)
    blockchain_address = models.CharField(default="", max_length=500)

    info_message_id = models.CharField(default="", max_length=500)
    info_message_address = models.CharField(default="", max_length=500)

    transaction_type = models.IntegerField(
        default=constants.TRANSACTION_TYPE_EXTERNAL,
        choices=constants.TRANSACTION_TYPE_CHOICES,
    )
    status = models.IntegerField(
        default=constants.TRANSACTION_STATUS_CREATED,
        choices=constants.TRANSACTION_STATUS_CHOICES,
    )

    deleted = models.BooleanField(default=False)
    _source_quantity = models.DecimalField(
        max_digits=25, decimal_places=3, default=None, null=True, blank=True
    )
    _destination_quantity = models.DecimalField(
        default=0.0, max_digits=25, decimal_places=3, null=True, blank=True
    )

    source_batches = models.ManyToManyField(
        "products.Batch",
        through="SourceBatch",
        related_name="outgoing_transactions",
    )
    client_type = models.IntegerField(
        default=constants.CLIENT_WEB, choices=constants.CLIENT_CHOICES
    )
    verification_method = models.IntegerField(
        default=constants.VERIFICATION_METHOD_MANUAL,
        choices=constants.VERIFICATION_METHOD_CHOICES,
    )
    extra_fields = JSONField(blank=True, null=True)

    def __str__(self):
        """To perform function __str__."""
        transaction_object_strs = str(self.transaction_object).split("-")
        transaction_object_str = "-".join(transaction_object_strs[:-1]).strip()
        return "%s - %s" % (transaction_object_str, self.id)

    @property
    def verification(self):
        """Get the verification method or return None if it is manual and no
        invoice is provided.

        Returns:
            str or None: The verification method, or None if the
                         verification method is manual and no invoice is
                         provided.
        """
        if (
            self.verification_method == constants.VERIFICATION_METHOD_MANUAL
            and not self.invoice
        ):
            return None
        return self.verification_method

    def save(self, *args, **kwargs):
        """Overriding save method to update transaction number.

        Transaction number is always the django id + 2200
        """
        self.new_instance = not self.pk
        super(Transaction, self).save(*args, **kwargs)
        self.copy_invoice_to_attachment()
        if not self.number:
            self.number = self.pk + 2200
            self.save()

    @property
    def transaction_object(self):
        """To perform function transaction_object."""
        if self.is_external:
            return self.externaltransaction
        else:
            return self.internaltransaction

    @property
    def premium_paid(self):
        """Returns premiums related to transactions."""
        return self.transaction_payments.filter(
            payment_type=TRANSACTION_PREMIUM
        )

    @property
    def source(self):
        """To perform function source."""
        return self.transaction_object.source

    @property
    def source_wallet(self):
        """To perform function source_wallet."""
        return self.transaction_object.source_wallet

    @property
    def destination(self):
        """To perform function stination."""
        return self.transaction_object.destination

    @property
    def destination_wallet(self):
        """To perform function stination_wallet."""
        return self.transaction_object.destination_wallet

    @property
    def is_external(self):
        """To perform function is_external."""
        if self.transaction_type == constants.TRANSACTION_TYPE_EXTERNAL:
            return True
        return False

    @property
    def is_internal(self):
        """To perform function is_internal."""
        if self.transaction_type == constants.TRANSACTION_TYPE_INTERNAL:
            return True
        return False

    @property
    def source_quantity(self):
        """To perform function source_quantity."""
        if self._source_quantity:
            return self._source_quantity
        qty = self.source_batch_objects.aggregate(
            total_quantity=models.Sum("quantity")
        )["total_quantity"]
        self._source_quantity = qty
        self.save()
        return self._source_quantity

    @property
    def destination_quantity(self):
        """To perform function stination_quantity."""
        if self._destination_quantity:
            return self._destination_quantity
        qty = self.result_batches.aggregate(
            total_quantity=models.Sum("initial_quantity")
        )["total_quantity"]
        self._destination_quantity = qty
        self.save()
        return self._destination_quantity

    @property
    def source_products(self):
        """To perform function source_products."""
        return Product.objects.filter(
            batches__outgoing_transactions=self
        ).distinct()

    @property
    def destination_products(self):
        """To perform function stination_products."""
        return Product.objects.filter(
            batches__source_transaction=self
        ).distinct()

    @property
    def product(self):
        """To perform function product."""
        return self.transaction_object.product

    @property
    def first_source_batch(self):
        """To perform function irst_source_batch."""
        return self.source_batch_objects.first()

    @property
    def supplier(self):
        """To perform function supplier."""
        if self.transaction_type == constants.TRANSACTION_TYPE_EXTERNAL:
            return self.externaltransaction.source
        elif self.transaction_type == constants.TRANSACTION_TYPE_INTERNAL:
            return self.internaltransaction.node

    def direction(self, node):
        """To perform function irection."""
        if self.transaction_type == constants.TRANSACTION_TYPE_EXTERNAL:
            if (
                self.externaltransaction.type
                == constants.EXTERNAL_TRANS_TYPE_REVERSAL
            ):
                return "Reversed"
            elif self.externaltransaction.source == node:
                return "Outgoing"
            elif self.externaltransaction.destination == node:
                return "Incoming"
            else:
                return "Other"
        elif self.transaction_type == constants.TRANSACTION_TYPE_INTERNAL:
            return self.internaltransaction.node

    def get_absolute_source_products(self):
        """To perform function get_absolute_source_products."""
        if self.transaction_type == constants.TRANSACTION_TYPE_EXTERNAL:
            return self.source_products
        else:
            if (
                self.internaltransaction.mode
                != constants.TRANSACTION_MODE_SYSTEM
            ):
                return self.source_products

        from v2.products.models import Product

        products = Product.objects.none()

        for parent in self.parents.all():
            products |= parent.get_absolute_source_products()
        return products.order_by().distinct("id")

    def get_parent_transactions(self, only_internal=False):
        """To perform function get_parent_transactions."""
        parents = self.get_ancestors(include_self=True)

        if only_internal:
            return parents.filter(
                transaction_type=constants.TRANSACTION_TYPE_INTERNAL
            )

        parents = parents.filter(
            transaction_type=constants.TRANSACTION_TYPE_EXTERNAL
        )
        parents = parents.exclude(
            externaltransaction__type=constants.EXTERNAL_TRANS_TYPE_REVERSAL
        )
        parents = parents.exclude(status=constants.TRANSACTION_STATUS_DECLINED)
        if self.transaction_type == constants.TRANSACTION_TYPE_INTERNAL:
            parents |= Transaction.objects.filter(id=self.id).distinct("id")
        return parents

    def get_claims(self):
        """To perform function get_claims."""
        claims = (
            AttachedBatchClaim.objects.filter(
                batch__in=self.result_batches.all(),
                attached_from__in=[
                    claims_constants.ATTACHED_FROM_TRANSACTION,
                    claims_constants.ATTACHED_BY_INHERITANCE,
                ],
            )
            .order_by()
            .distinct("claim")
        )
        return claims

    @property
    def includable_in_chain(self):
        """To perform function includable_in_chain."""
        if self.transaction_type == constants.TRANSACTION_TYPE_INTERNAL:
            return False
        if (
            self.externaltransaction.type
            == constants.EXTERNAL_TRANS_TYPE_REVERSAL
        ):
            return False
        if (
            self.externaltransaction.status
            == constants.TRANSACTION_STATUS_DECLINED
        ):
            return False
        return True

    def get_parent_actors_levels(self, level=0):
        """To perform function get_parent_actors_levels."""
        local_level_data = {}
        level_next = level
        if self.includable_in_chain:
            level_next = level + 1
            from v2.supply_chains.models import Node

            if level == 0:
                dest_actor = Node.objects.filter(
                    id=self.externaltransaction.destination.id
                )
                local_level_data = comm_lib._safe_join_to_query(
                    local_level_data, 0, dest_actor
                )
            source_actor = Node.objects.filter(
                id=self.externaltransaction.source.id
            )
            local_level_data = comm_lib._safe_join_to_query(
                local_level_data, level + 1, source_actor
            )
        for parent in self.parents.all():
            sub_level_data = parent.get_parent_actors_levels(level=level_next)
            for lvl, lvl_actors in sub_level_data.items():
                local_level_data = comm_lib._safe_join_to_query(
                    local_level_data, lvl, lvl_actors
                )
        return local_level_data

    def update_cache(self):
        """Update cache by force reloading."""
        from .serializers.consumer_interface import serialize_transaction

        serialize_transaction(self, force_reload=True)
        return True

    def log_blockchain_transaction(self):
        """To perform function log_blockchain_transaction."""
        self.transaction_object.log_blockchain_transaction()

    def log_activity(self):
        """To perform function log_activity."""
        self.transaction_object.log_activity()

    def notify(self):
        """To perform function notify."""
        self.transaction_object.notify()

    @property
    def wallet_type(self):
        """To perform function wallet_type."""
        return self.transaction_object.wallet_type

    @property
    def explorer_url(self):
        """To perform function xplorer_url."""
        wallet_type = self.wallet_type
        if wallet_type == sc_constants.BLOCKCHAIN_WALLET_TYPE_TOPL:
            return settings.TOPL_TRANSACTION_EXPLORED.format(
                address=self.blockchain_address
            )
        if wallet_type == sc_constants.BLOCKCHAIN_WALLET_TYPE_HEDERA:
            return settings.HEDERA_TRANSACTION_EXPLORER.format(
                address=self.blockchain_id
            )
        return ""

    @property
    def info_explorer_url(self):
        """To perform function info_explorer_url."""
        if self.info_message_address:
            return settings.HEDERA_TRANSACTION_EXPLORER.format(
                address=self.info_message_id
            )
        return ""

    def invalidate_cache(self):
        """To perform function invalidate_cache."""
        key = "transaction_base_data_%s" % self.idencode
        cache.delete(key)

    def copy_invoice_to_attachment(self):
        """Copy the invoice to a transaction attachment.

        This method copies the invoice file associated with the
        transaction and creates a new transaction attachment with the
        invoice file attached. The attachment is linked to the
        transaction and associated with the relevant node (either the
        source or destination node).
        """
        if self.new_instance and self.invoice:
            node = self.source if self.source.type == 1 else self.destination
            self.attachments.model.objects.create(
                transaction_id=self.id,
                name="Receipt",
                node_id=node.id,
                attachment=self.invoice,
            )


class ExternalTransaction(
    Transaction, AbstractTokenTransaction, AbstractConsensusMessage
):
    """Model for External Transactions.

    Attributes:
        external_id(str) : External ID of transaction.
        source(obj)     : Source Node of transaction.
        destination(obj): Destination Node of transaction.
        price(float)     : Price paid for transaction.
        currency        : Currency of payment.
        type            : Type of transaction incoming/outgoing.

    Property:
        source_quantity: Dynamically calculates the source quantity
                         by taking the sum of quantities taken from
                         all source batches.
    """
    external_id = models.CharField(max_length=100, null=True, blank=True)
    source = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="outgoing_transactions",
    )
    source_wallet = models.ForeignKey(
        "supply_chains.BlockchainWallet",
        on_delete=models.CASCADE,
        related_name="outgoing_transactions",
        null=True,
        blank=True,
        default=None,
    )
    destination = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="incoming_transactions",
    )
    destination_wallet = models.ForeignKey(
        "supply_chains.BlockchainWallet",
        on_delete=models.CASCADE,
        related_name="incoming_transactions",
        null=True,
        blank=True,
        default=None,
    )
    product_price = models.FloatField(default=None, null=True, blank=True)
    price = models.FloatField(default=None, null=True, blank=True)
    currency = models.CharField(
        choices=CURRENCY_CHOICES,
        max_length=5,
        default=None,
        null=True,
        blank=True,
    )
    type = models.IntegerField(
        default=constants.EXTERNAL_TRANS_TYPE_OUTGOING,
        choices=constants.EXTERNAL_TRANS_TYPE_CHOICES,
    )
    verification_latitude = models.FloatField(default=0.0)
    verification_longitude = models.FloatField(default=0.0)
    buyer_ref_number = models.CharField(
        max_length=200, default="", null=True, blank=True
    )
    seller_ref_number = models.CharField(
        max_length=200, default="", null=True, blank=True
    )

    objects = ExternalTransactionQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        kwargs["transaction_type"] = constants.TRANSACTION_TYPE_EXTERNAL
        super(ExternalTransaction, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        """Saves the instance and performs additional operations.

        This method overrides the default save method of the model. It first
        saves the instance to the database using the parent class's 'save'
        method. Then, it calls the `update_payments` method to perform any
        necessary operations related to payments.

        Parameters:
        - *args: Variable-length argument list.
        - **kwargs: Arbitrary keyword arguments.
        """
        super().save(*args, **kwargs)
        self.update_payments()

    def __str__(self):
        """To perform function __str__."""
        return "%s to %s - %s" % (
            self.source.full_name,
            self.destination.full_name,
            self.id,
        )

    @property
    def wallet_type(self):
        """To perform function wallet_type."""
        if not self.source_wallet or not self.destination_wallet:
            return sc_constants.BLOCKCHAIN_WALLET_TYPE_TOPL
        if (
            self.source_wallet.wallet_type
            != self.destination_wallet.wallet_type
        ):
            raise AttributeError("Invalid wallets combination")
        if not self.source_wallet:
            return sc_constants.BLOCKCHAIN_WALLET_TYPE_TOPL
        return self.source_wallet.wallet_type

    def notify(self):
        """To perform function notify."""
        notifications = get_notification_data(self)
        for notification in notifications:
            Notification.notify(**notification)

    @property
    def result_batch(self):
        """To perform function result_batch."""
        return self.result_batches.first()

    @property
    def product(self):
        """To perform function product."""
        return self.destination_products.first()

    def log_activity(self):
        """To perform function log_activity."""
        supply_chain = self.source_batches.first().product.supply_chain
        if self.type in [
            constants.EXTERNAL_TRANS_TYPE_INCOMING,
            constants.EXTERNAL_TRANS_TYPE_OUTGOING,
        ]:
            Activity.log(
                event=self,
                activity_type=act_constants.NODE_SENT_STOCK,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_EXT_TRANSACTION,
                node=self.source,
                supply_chain=supply_chain,
            )
            Activity.log(
                event=self,
                activity_type=act_constants.NODE_RECEIVED_STOCK,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_EXT_TRANSACTION,
                node=self.destination,
                supply_chain=supply_chain,
            )
        elif self.type == constants.EXTERNAL_TRANS_TYPE_REVERSAL:
            Activity.log(
                event=self,
                activity_type=act_constants.NODE_USER_REJECTED_TRANSACTION,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_EXT_TRANSACTION,
                node=self.source,
                supply_chain=supply_chain,
            )
            Activity.log(
                event=self,
                activity_type=act_constants.NODE_STOCK_WAS_RETURNED,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_EXT_TRANSACTION,
                node=self.destination,
                supply_chain=supply_chain,
            )
        return True

    @property
    def is_rejectable(self):
        """To perform function is_rejectable."""
        if self.type == constants.EXTERNAL_TRANS_TYPE_REVERSAL:
            # If the transaction is already a reversed transaction,
            # it cannot be further rejected
            return False
        if self.status == constants.TRANSACTION_STATUS_DECLINED:
            # Cannot decline already declined transaction
            return False
        if self.source.is_farm():
            # Farmer transaction is created as incoming from company.
            # So company cannot reject it again.
            return False
        batch_used = any(
            [batch.is_used for batch in self.result_batches.all()]
        )
        if batch_used:
            return False
        claims_attached = self.result_batch.claims.filter(
            attached_from=claims_constants.ATTACHED_DIRECTLY
        ).exists()
        if claims_attached:
            return False
        return True

    def perspective_type(self, node):
        """To perform function perspective_type."""
        if self.type == constants.EXTERNAL_TRANS_TYPE_REVERSAL:
            return constants.EXTERNAL_TRANS_TYPE_REVERSAL
        elif node == self.source:
            return constants.EXTERNAL_TRANS_TYPE_OUTGOING
        elif node == self.destination:
            return constants.EXTERNAL_TRANS_TYPE_INCOMING

    @property
    def sender_id(self):
        """To perform function sender_id."""
        if not self.source_wallet or not self.source_wallet.account_id:
            raise ValueError(
                "Blockchain account has not been set-up for"
                f" {self.source.full_name}"
            )
        return self.source_wallet.account_id

    @property
    def sender_private(self):
        """To perform function sender_private."""
        if not self.source_wallet or not self.source_wallet.decrypted_private:
            raise ValueError(
                "Blockchain account has not been set-up for"
                f" {self.source.full_name}"
            )
        return self.source_wallet.decrypted_private

    @property
    def initiator_wallet(self):
        """To perform function initiator_wallet."""
        return self.source_wallet

    @property
    def receiver_id(self):
        """To perform function receiver_id."""
        if (
            not self.destination_wallet
            or not self.destination_wallet.account_id
        ):
            raise ValueError(
                "Blockchain account has not been set-up for"
                f" {self.destination.full_name}"
            )
        return self.destination_wallet.account_id

    @property
    def quantity(self):
        """To perform function quantity."""
        return self.result_batch.initial_quantity_in_gram

    @property
    def token_id(self):
        """To perform function token_id."""
        return self.product.token_id

    def pre_check(self):
        """To perform function pre_check."""
        success, message = super(ExternalTransaction, self).pre_check()
        if not success:
            return success, message

        from v2.products.models import NodeProduct

        if self.blockchain_address or self.blockchain_id:
            return False, "Transaction already logged"
        if self.type == constants.EXTERNAL_TRANS_TYPE_INCOMING:
            pending = False
            for b in self.source_batches.filter(blockchain_id=""):
                b.create_blockchain_asset()
                pending = True
            if pending:
                return False, "Pending asset found, Creating Assets first"
        if not self.destination_wallet:
            if not self.destination.hedera_wallet:
                self.destination.setup_blockchain_account()
                return False, "Setting up Destination wallet"
            self.destination_wallet = self.destination.blockchain_wallet
            self.save()
        else:
            if (
                self.destination_wallet.wallet_type
                != sc_constants.BLOCKCHAIN_WALLET_TYPE_HEDERA
            ):
                return False, "Can log only hedera transactions"
        if not self.source_wallet:
            if not self.source.hedera_wallet:
                self.source.setup_blockchain_account()
                return False, "Setting up Source wallet"
            self.source_wallet = self.source.blockchain_wallet
            self.save()
        else:
            if (
                self.source_wallet.wallet_type
                != sc_constants.BLOCKCHAIN_WALLET_TYPE_HEDERA
            ):
                return False, "Can log only hedera transactions"

        np, created = NodeProduct.objects.get_or_create(
            node_wallet=self.destination_wallet,
            product=self.result_batch.product,
        )
        if not np.kyc_completed:
            np.perform_kyc()
            return False, "Result product not KYCed to Destination wallet"
        return True, "Pre-check success"

    def log_blockchain_transaction(self):
        """To perform function log_blockchain_transaction."""
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

    def validate_callback(self, response):
        """To perform function validate_callback."""
        if "message" in response:
            if "TOKEN_NOT_ASSOCIATED_TO_ACCOUNT" in response["message"]:
                from v2.products.models import NodeProduct

                np, c = NodeProduct.objects.get_or_create(
                    node_wallet=self.destination_wallet,
                    product=self.result_batch.product,
                )
                np.associated = False
                np.kyc_completed = False
                np.save()
                np.associate(retry=True)
                return False
            elif "ACCOUNT_KYC_NOT_GRANTED_FOR_TOKEN" in response["message"]:
                from v2.products.models import NodeProduct

                np, c = NodeProduct.objects.get_or_create(
                    node_wallet=self.destination_wallet,
                    product=self.result_batch.product,
                )
                np.kyc_completed = False
                np.save()
                np.perform_kyc()
                return False
            else:
                capture_message(response["message"])
                return False
        return True

    def update_hedera_data(self, response):
        """To perform function update_hedera_data."""
        if not self.validate_callback(response):
            return False

        self.blockchain_id = response["data"]["transactionId"]
        self.blockchain_address = response["data"]["transactionHash"]
        self.save()
        if (
            self.result_batch.blockchain_hash
            or self.result_batch.blockchain_id
        ):
            capture_message("Batch hash exists before transaction is logged")
        else:
            rb = self.result_batch
            rb.node_wallet = self.destination_wallet
            rb.blockchain_id = response["data"]["transactionId"]
            rb.blockchain_hash = response["data"]["transactionHash"]
            rb.save()
        self.post_success()
        return True

    def post_success(self):
        """To perform function post_success."""
        self.submit_info_message()
        self.update_cache()
        for rb in self.result_batches.all():
            for tr in rb.outgoing_transactions.all():
                tr.log_blockchain_transaction()
        for sbo in self.source_batch_objects.all():
            sbo.blockchain_id = self.blockchain_id
            sbo.blockchain_address = self.blockchain_address
            sbo.save()
        return True

    def message_pre_check(self):
        """To perform function message_pre_check."""
        success, message = super(ExternalTransaction, self).message_pre_check()
        if not success:
            return success, message
        if not self.blockchain_address:
            return False, "BC hash exists. Already logged"
        if self.info_message_address:
            return False, "Info hash exists. Already logged"
        return True, "Pre-check success"

    def get_additional_info(self):
        """To perform function get_additional_info."""
        data = {
            "number": self.number,
            "date": self.date.strftime("%d %B %Y"),
            "product_name": self.product.name,
            "unit": self.result_batch.unit_display,
            "quantity": self.result_batch.initial_quantity_in_gram,
            "supply_chain": self.product.supply_chain.name,
            "sender": self.source.full_name,
            "sender_public": self.source_wallet.public,
            "receiver": self.destination.full_name,
            "receiver_public": self.destination_wallet.public,
            "source_batches": [
                batch.blockchain_hash for batch in self.source_batches.all()
            ],
        }
        return data

    @property
    def topic_id(self):
        """To perform function topic_id."""
        return settings.HEDERA_TRANSACTION_TOPIC_ID

    @property
    def message(self):
        """To perform function message."""
        return json.dumps(self.get_additional_info(), cls=DjangoJSONEncoder)

    def submit_info_message(self):
        """To perform function submit_info_message."""
        success, message = self.message_pre_check()
        if not success:
            print(f"{self.__class__.__name__} - {self.id} | {message}")
            return False
        try:
            self.initialize_message(self.creator)
            self.submit_message_request.send()
            return True
        except Exception as e:
            capture_exception(e)
            return False

    def update_message_hash(self, bc_data):
        """To update hash on callback from blockchain node."""
        if not bc_data:
            return False
        self.info_message_id = bc_data["transactionId"]
        self.info_message_address = bc_data["transactionHash"]
        self.save()
        self.update_cache()
        return True

    def update_payments(self):
        """Update price against transaction to payment."""

        # create payment if only after price is set
        if self.price:
            payment, _ = Payment.objects.get_or_create(
                transaction=self, premium=None
            )
            payment.amount = self.price
            payment.save()

        # refresh payments to update invoice
        if self.invoice and not self.new_instance:
            [payment.save() for payment in self.transaction_payments.all()]


class InternalTransaction(Transaction, AbstractConsensusMessage):
    """Model for Internal transactions.

    Attributes:
        node(obj)           : Node creating the transaction.
        by_products(objs)   : By product transaction of the main
                              transaction.
        type(int)           : Internal transaction type
                              (processing/loss)
    """

    node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        default=None,
        null=True,
        related_name="internaltransactions",
    )
    node_wallet = models.ForeignKey(
        "supply_chains.BlockchainWallet",
        on_delete=models.CASCADE,
        default=None,
        null=True,
        related_name="internaltransactions",
    )
    type = models.IntegerField(
        default=constants.INTERNAL_TRANS_TYPE_PROCESSING,
        choices=constants.INTERNAL_TRANS_TYPE_CHOICES,
    )
    mode = models.IntegerField(
        default=constants.TRANSACTION_MODE_MANUAL,
        choices=constants.TRANSACTION_MODE_CHOICES,
    )

    objects = InternalTransactionQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        kwargs["transaction_type"] = constants.TRANSACTION_TYPE_INTERNAL
        super(InternalTransaction, self).__init__(*args, **kwargs)

    def __str__(self):
        """To perform function __str__."""
        return "%s %s - %s" % (
            self.node.full_name,
            self.get_type_display(),
            self.id,
        )

    @property
    def wallet_type(self):
        """To perform function wallet_type."""
        return (
            self.node_wallet.wallet_type
            if self.node_wallet
            else sc_constants.BLOCKCHAIN_WALLET_TYPE_TOPL
        )

    @property
    def source(self):
        """To perform function source."""
        return self.node

    @property
    def source_wallet(self):
        """To perform function source_wallet."""
        return self.node_wallet

    @property
    def destination(self):
        """To perform function stination."""
        return self.node

    @property
    def destination_wallet(self):
        """To perform function stination_wallet."""
        return self.node_wallet

    def notify(self):
        """Notification is not required for internal transactions.

        but added for consistency
        """
        pass

    @property
    def product(self):
        """To perform function product."""
        try:
            return self.result_batches.first().product
        except Exception:
            return self.source_batches.first().product

    @property
    def source_batch_info(self):
        """To perform function source_batch_info."""
        batches = [b for b in self.source_batch_objects.all()]
        batch_initial = batches[:2]
        batch_rest = batches[2:]
        if not batch_rest:
            batch_string = comm_lib._list_to_sentence(
                [
                    "%s%s of %s"
                    % (bat.quantity, bat.unit_display, bat.batch.product.name)
                    for bat in batch_initial
                ]
            )
        else:
            batch_string = ", ".join(
                [
                    "%s%s of %s"
                    % (bat.quantity, bat.unit_display, bat.batch.product.name)
                    for bat in batch_initial
                ]
            )
            rest_count = len(batch_rest)
            if rest_count == 1:
                batch_string += " and 1 other"
            else:
                batch_string += " and %d other" % rest_count
        return batch_string

    @property
    def result_batch_info(self):
        """To perform function result_batch_info."""
        batches = [b for b in self.result_batches.all()]
        batch_initial = batches[:2]
        batch_rest = batches[2:]
        if not batch_rest:
            batch_string = comm_lib._list_to_sentence(
                [
                    "%s%s of %s"
                    % (
                        bat.initial_quantity,
                        bat.unit_display,
                        bat.product.name,
                    )
                    for bat in batch_initial
                ]
            )
        else:
            batch_string = ", ".join(
                [
                    "%s%s of %s"
                    % (
                        bat.initial_quantity,
                        bat.unit_display,
                        bat.product.name,
                    )
                    for bat in batch_initial
                ]
            )
            rest_count = len(batch_rest)
            if rest_count == 1:
                batch_string += " and 1 other"
            else:
                batch_string += " and %d other" % rest_count
        return batch_string

    def log_activity(self):
        """To perform function log_activity."""
        supply_chain = self.source_batches.first().product.supply_chain
        if self.mode == constants.TRANSACTION_MODE_MANUAL:
            activity_type = act_constants.NODE_USER_INTERNAL_TRANSACTION
        else:
            activity_type = act_constants.NODE_SYSTEM_INTERNAL_TRANSACTION

        source_string = self.source_batch_info
        result_string = self.result_batch_info

        message = ""
        if self.type == constants.INTERNAL_TRANS_TYPE_PROCESSING:
            message = "Converted %s to %s" % (source_string, result_string)
        if self.type == constants.INTERNAL_TRANS_TYPE_MERGE:
            message = "Merged %s" % source_string
        if self.type == constants.INTERNAL_TRANS_TYPE_LOSS:
            message = "Removed %s" % source_string
        Activity.log(
            event=self,
            activity_type=activity_type,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_INT_TRANSACTION,
            user=self.creator,
            node=self.node,
            supply_chain=supply_chain,
            context={"message": message},
        )

    @property
    def topic_id(self):
        """To perform function topic_id."""
        return settings.HEDERA_TRANSACTION_TOPIC_ID

    @property
    def message(self):
        """To perform function message."""
        sb_texts = [
            "%s%s of %s"
            % (bat.quantity, bat.unit_display, bat.batch.product.name)
            for bat in self.source_batch_objects.all()
        ]
        source_batch_info = comm_lib._list_to_sentence(sb_texts)
        rb_texts = [
            "%s%s of %s"
            % (bat.initial_quantity, bat.unit_display, bat.product.name)
            for bat in self.result_batches.all()
        ]
        result_batch_info = comm_lib._list_to_sentence(rb_texts)
        data = {
            "source_batches": source_batch_info,
            "result_batches": result_batch_info,
        }
        return json.dumps(data, cls=DjangoJSONEncoder)

    @property
    def short_message(self):
        """To perform function short_message."""
        sb_texts = [
            "%s%s of %s"
            % (bat.quantity, bat.unit_display, bat.batch.product.name)
            for bat in self.source_batch_objects.all()
        ]
        rb_texts = [
            "%s%s of %s"
            % (bat.initial_quantity, bat.unit_display, bat.product.name)
            for bat in self.result_batches.all()
        ]
        if len(sb_texts) > 10:
            source_batch_info = (
                comm_lib._list_to_sentence(sb_texts[:10])
                + f" and {len(sb_texts) - 10} other batches"
            )
        else:
            source_batch_info = comm_lib._list_to_sentence(sb_texts[:10])
        if len(rb_texts) > 10:
            result_batch_info = (
                comm_lib._list_to_sentence(rb_texts[:10])
                + f" and {len(rb_texts) - 10} other batches"
            )
        else:
            result_batch_info = comm_lib._list_to_sentence(rb_texts[:10])

        data = {
            "source_batches": source_batch_info,
            "result_batches": result_batch_info,
        }
        return json.dumps(data, cls=DjangoJSONEncoder)

    def log_blockchain_transaction(self):
        """There isn't any transaction in the blockchain for internal
        transactions.

        All source batches will be wiped and new batches will be
        created.
        """
        # sbo_count = self.source_batch_objects.count()
        # rb_count = self.result_batches.count()
        # capture_message(f"Burning {sbo_count} batch(es)
        # and minting {rb_count} batch(es).")
        for sbo in self.source_batch_objects.all():
            sbo.burn_source_asset(self.creator)
        for rb in self.result_batches.all():
            rb.create_blockchain_asset()

        success, message = self.message_pre_check()
        if not success:
            print(f"{self.__class__.__name__} - {self.id} | {message}")
            return False
        try:
            self.initialize_message(self.creator)
            self.submit_message_request.send()
            return True
        except Exception as e:
            capture_exception(e)
            return False

    def update_message_hash(self, bc_data):
        """To update hash on callback from blockchain node."""
        if not bc_data:
            return False
        self.blockchain_id = bc_data["transactionId"]
        self.blockchain_address = bc_data["transactionHash"]
        self.info_message_id = bc_data["transactionId"]
        self.info_message_address = bc_data["transactionHash"]
        self.save()
        self.post_success()
        return True

    def post_success(self):
        """To perform function post_success."""
        self.update_cache()
        return True


class SourceBatch(
    AbstractBaseModel, AbstractBurnedToken, AbstractConsensusMessage
):
    """Model contains data of how much quantity of items from which batch(es)
    were taken to create the transaction.

    Attributes:
        transaction(obj)    : Transaction created using the batch.
        batch(obj)          : Batch that was used for the transaction.
        quantity(float)     : Quantity used from the batch for the
                              transaction.
    """

    transaction = models.ForeignKey(
        Transaction,
        related_name="source_batch_objects",
        on_delete=models.CASCADE,
    )
    batch = models.ForeignKey(
        "products.Batch",
        on_delete=models.CASCADE,
        related_name="outgoing_transaction_objects",
    )
    quantity = models.DecimalField(
        default=0.0, max_digits=25, decimal_places=3
    )
    unit = models.IntegerField(
        choices=product_constants.UNIT_CHOICES,
        default=product_constants.UNIT_KG,
    )
    blockchain_id = models.CharField(default="", max_length=500)
    blockchain_address = models.CharField(default="", max_length=500)

    info_message_id = models.CharField(default="", max_length=500)
    info_message_address = models.CharField(default="", max_length=500)

    def __str__(self):
        """To perform function __str__."""
        return "%s - %s" % (self.transaction, self.id)

    @property
    def unit_display(self):
        """To perform function unit_display."""
        return self.get_unit_display()

    @property
    def quantity_in_gram(self):
        """To perform function quantity_in_gram."""
        return (
            float(self.quantity)
            * product_constants.UNIT_CONVERSION_FACTOR[self.unit]
        )

    @property
    def owner_id(self):
        """To perform function owner_id."""
        return self.batch.node_wallet.account_id

    @property
    def owner_private(self):
        """To perform function owner_private."""
        return self.batch.node_wallet.decrypted_private

    @property
    def initiator_wallet(self):
        """To perform function initiator_wallet."""
        return self.batch.node_wallet

    @property
    def quantity_to_burn(self):
        """To perform function quantity_to_burn."""
        return self.quantity_in_gram

    @property
    def token_id(self):
        """To perform function token_id."""
        return self.batch.product.token_id

    def pre_check(self):
        """To perform function pre_check."""
        success, message = super(SourceBatch, self).pre_check()
        if not success:
            return success, message

        if self.blockchain_id or self.blockchain_address:
            return False, "Blockchain id or address exists."
        if not self.transaction.is_internal:
            return False, "Transaction is not internal"
        if not self.batch.blockchain_hash:
            self.batch.create_blockchain_asset()
            return False, "Batch is not minted, or received"
        return True, "Pre-check success"

    def burn_source_asset(self, user=None):
        """To perform function burn_source_asset."""
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

    def validate_callback(self, response):
        """To perform function validate_callback."""
        return True

    def update_hedera_data(self, response):
        """To perform function update_hedera_data."""
        if not self.validate_callback(response):
            return False

        self.blockchain_id = response["data"]["transactionId"]
        self.blockchain_address = response["data"]["transactionHash"]
        self.save()
        self.post_success()  # Add any other actions that need
        # to be taken in post_success()
        return True

    def post_success(self):
        """To perform function post_success."""
        self.submit_info_message()
        return True

    def message_pre_check(self):
        """To perform function message_pre_check."""
        success, message = super(SourceBatch, self).message_pre_check()
        if not success:
            return success, message
        if not self.blockchain_address:
            return False, "BC hash exists. Already logged"
        if self.info_message_address:
            return False, "Info hash exists. Already logged"
        return True, "Pre-check success"

    def get_additional_info(self):
        """To perform function get_additional_info."""
        data = {
            "batch_number": self.batch.number,
            "date": self.transaction.date.strftime("%d %B %Y"),
            "product_name": self.batch.product.name,
            "unit": self.unit_display,
            "quantity": self.quantity,
            "supply_chain": self.batch.product.supply_chain.name,
            "sender": self.transaction.supplier.full_name,
            "sender_public": self.batch.node_wallet.public,
            "transaction_number": self.transaction.number,
            "reason": "Wiping asset as part of internal transaction",
        }
        return data

    @property
    def topic_id(self):
        """To perform function topic_id."""
        return settings.HEDERA_TRANSACTION_TOPIC_ID

    @property
    def message(self):
        """To perform function message."""
        return json.dumps(self.get_additional_info(), cls=DjangoJSONEncoder)

    def submit_info_message(self):
        """To perform function submit_info_message."""
        success, message = self.message_pre_check()
        if not success:
            print(f"{self.__class__.__name__} - {self.id} | {message}")
            return False
        try:
            self.initialize_message(self.creator)
            self.submit_message_request.send()
            return True
        except Exception as e:
            capture_exception(e)
            return False

    def update_message_hash(self, bc_data):
        """To update hash on callback from blockchain node."""
        if not bc_data:
            return False
        self.info_message_id = bc_data["transactionId"]
        self.info_message_address = bc_data["transactionHash"]
        self.save()
        return True


class TransactionAttachment(AbstractBaseModel):
    """
    Represents an attachment associated with a transaction.

    ...

    Fields
    ------
    transaction : ForeignKey
        The transaction to which the attachment belongs.
    attachment : FileField
        The file field for storing the attachment file.
    node : ForeignKey
        The node associated with the transaction attachment.
    name : CharField
        The name of the attachment.
    """

    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="attachments"
    )
    attachment = models.FileField(
        upload_to=_get_file_path, blank=True, null=True
    )
    node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="transaction_attachments",
    )
    name = models.CharField(max_length=60)

    objects = TransactionAttachmentQuerySet.as_manager()

    def __str__(self):
        """Returns a string representation of the transaction attachment."""
        file_name = os.path.basename(self.attachment.name)
        return f"{self.transaction.number} : {file_name} - {self.pk}"
