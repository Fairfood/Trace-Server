"""Models for products."""
import datetime
import json

from common.library import _get_file_path
from common.models import AbstractBaseModel
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from sentry_sdk import capture_exception, capture_message
from v2.blockchain.models.create_token import AbstractToken
from v2.blockchain.models.kyc_token import AbstractKYCToken
from v2.blockchain.models.mint_token import AbstractMintedToken
from v2.blockchain.models.submit_message import AbstractConsensusMessage
from v2.claims import constants as claims_constants
from v2.supply_chains import constants as sc_constants
from v2.transactions import constants as trans_constants

from ..supply_chains.constants import NODE_TYPE_COMPANY, NODE_TYPE_FARM
from ..transactions.constants import TRANSACTION_TYPE_INTERNAL
from . import constants
from .managers import (BatchFarmerMappingQuerySet, BatchQuerySet,
                       ProductQuerySet)

# Create your models here.


# Create your models here.


class Product(AbstractBaseModel, AbstractToken):
    """Table for storing products.

    Attributes:
        external_id(str): External ID of the product.
        name(str): Product name.
        supply_chain(str): Name of the supply chain of which the product is a
                            part of.
        description(str): Product description
    """
    external_id = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=1000, default="", blank=True)
    image = models.FileField(
        upload_to=_get_file_path, null=True, default=None, blank=True
    )
    image_name = models.CharField(max_length=1000, default="", blank=True)
    supply_chain = models.ForeignKey(
        "supply_chains.SupplyChain",
        on_delete=models.CASCADE,
        related_name="products",
    )
    type = models.IntegerField(
        choices=constants.PRODUCT_TYPE_CHOICES,
        default=constants.PRODUCT_TYPE_GLOBAL,
    )
    owners = models.ManyToManyField("supply_chains.Node", blank=True)
    deleted = models.BooleanField(default=False)

    token_id = models.CharField(
        max_length=50, null=True, blank=True, default=""
    )

    objects = ProductQuerySet.as_manager()

    def __str__(self):
        """To perform function __str__."""
        return f"{self.name}({self.supply_chain.name} - {self.pk})"

    def grant_access_to(self, node):
        """Grant access to node."""
        if self.type == constants.PRODUCT_TYPE_LOCAL:
            self.owners.add(node)
            self.save()
        return True

    @property
    def token_name(self):
        """Get token name."""
        name = self.name + "-" * (5 - len(self.name))
        return name[:10]

    def validate_callback(self, data):
        """Validate callback."""
        if Product.objects.filter(token_id=data["tokenId"]).exists():
            self.block_chain_request.delete()
            self.create_token()
            return False
        return True

    def update_token_id(self, data):
        """Update token ID."""
        if not self.validate_callback(data):
            return False
        self.token_id = data["tokenId"]
        self.save()
        self.post_success()
        return True

    def pre_check(self):
        """Perform pre-check."""
        success, message = super(Product, self).pre_check()
        if not success:
            return success, message
        if self.token_id:
            return False, "Token already created"
        return True, "Pre-check success"

    def create_token(self):
        """Create token."""
        success, message = self.pre_check()
        if not success:
            print(f"{self.__class__.__name__} - {self.id} | {message}")
            return False
        try:
            self.initialize()
            self.block_chain_request.send()
            return True
        except Exception as e:
            capture_exception(e)
            return False

    def post_success(self):
        """Perform post success."""
        for batch in self.batches.all():
            batch.create_blockchain_asset()
        return True


class NodeProduct(AbstractBaseModel, AbstractKYCToken):
    """Model to store Node to Product relation. It is used to record token
    association and KYC status.

    Attributes:
        product(obj)        : Product that is added
        node(obj)           : Node to which product is added
        associated(bool)    : Whether the token is associated in blockchain
        association_hash(str):Hash received when associating token
        kyc_completed(bool) : Whether KYC is completed in blockchain
        kyc_hash(str)       : Hash received when doing kyc for token.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="nodes"
    )
    node_wallet = models.ForeignKey(
        "supply_chains.BlockchainWallet",
        on_delete=models.CASCADE,
        related_name="node_products",
    )
    association = models.ForeignKey(
        "supply_chains.WalletTokenAssociation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="associated_products",
    )
    associated = models.BooleanField(default=False)
    association_hash = models.CharField(
        max_length=200, null=True, blank=True, default=""
    )
    kyc_completed = models.BooleanField(default=False)
    kyc_hash = models.CharField(
        max_length=200, null=True, blank=True, default=""
    )

    class Meta:
        unique_together = ("product", "node_wallet")

    def __str__(self):
        """To perform function __str__."""
        return (
            f"{self.node_wallet.node.full_name} {self.product.name} -"
            f" {self.id}"
        )

    @property
    def token_id(self):
        """Get token ID."""
        return self.product.token_id

    @property
    def account_id(self):
        """Get account ID."""
        return self.node_wallet.account_id

    def batches(self):
        """Get batches."""
        return self.product.batches.filter(node=self.node_wallet.node)

    def pre_check(self):
        """Perform pre-check."""
        success, message = super(NodeProduct, self).pre_check()
        if not success:
            return success, message
        if not self.batches().exists():
            return (
                False,
                "KYC postponed as batch does not exist for the product.",
            )
        if (
            self.node_wallet.wallet_type
            != sc_constants.BLOCKCHAIN_WALLET_TYPE_HEDERA
        ):
            return False, "KYC only required for hedera accounts"
        if not Batch.objects.filter(
            product=self.product, node=self.node_wallet.node
        ).exists():
            return (
                False,
                "No batch for the node product combination. KYC Skipped.",
            )

        if not self.associated:
            from v2.supply_chains.models import WalletTokenAssociation

            WalletTokenAssociation.create_association(
                wallet=self.node_wallet, supply_chain=self.product.supply_chain
            )
            return False, "Token not associated."
        return True, "Pre-check success"

    def associate(self, retry=False):
        """Associate request."""
        if self.association:
            if not retry:
                return False
            if self.association.block_chain_request.is_pending():
                return False
            if self.association.associated_products.count() <= 1:
                self.association.block_chain_request.retry()
                return True
        if (
            self.node_wallet.wallet_type
            != sc_constants.BLOCKCHAIN_WALLET_TYPE_HEDERA
        ):
            print("Association only needed for Hedera")
            return False
        from v2.supply_chains.models import WalletTokenAssociation

        association = WalletTokenAssociation.objects.create(
            node_wallet=self.node_wallet,
            supply_chain=self.product.supply_chain,
        )
        self.association = association
        self.save()
        association.associate_tokens()
        return association

    def perform_kyc(self, user=None):
        """Perform KYC."""
        success, message = self.pre_check()
        if not success:
            print(f"{self.__class__.__name__} - {self.id} | {message}")
            return False
        try:
            request = self.initialize(user)
            request.send()
            return True
        except Exception as e:
            capture_exception(e)
            return False

    def handle_kyc_success(self, resp_data):
        """handle KYC success."""
        if not resp_data["success"]:
            capture_message(resp_data["message"])
            print(f"KYC failed with message. {resp_data['message']}")
            return False
        self.kyc_completed = True
        self.save()
        self.post_success()
        return True

    def post_success(self):
        """Perform post success."""
        for bat in Batch.objects.filter(
            node_wallet=self.node_wallet, product=self.product
        ):
            bat.create_blockchain_asset()
        for it in self.node_wallet.incoming_transactions.filter(
            blockchain_address=""
        ):
            it.log_blockchain_transaction()
        for bm in self.node_wallet.migrations_to.filter(
            batch__product=self.product, blockchain_hash=""
        ):
            bm.perform_migration()
        return True


class Batch(AbstractBaseModel, AbstractMintedToken, AbstractConsensusMessage):
    """Model to store batches of product.

    Attributes:
        product(obj)                : Batch's product.
        node(obj)                   : Node that is in custody of the batch
        number(int)                 : Batch number for reference.
        source_transaction(obj)     : Transaction that created the Batch.
        name(str)                   : Name of batch to identify it. Mostly will
                                      mention who it was purchased from
        initial_quantity(float)     : Quantity when the batch was created.
        current_quantity(float)     : Quantity left in the batch.
        unit(int)                   : Unit of quantity.
        verified_percentage(float)  : What percentage of items in this batch
                                      is from a verified farmer.
        type(int)                   : Defines the type of batch
                                        - intermediate (Created as an
                                        intermediary batch during a
                                        transaction)
                                        - solid (Created as a result of a
                                        transaction done by the user)
    """
    navigate_id = models.CharField(max_length=100, null=True, blank=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="batches"
    )
    parents = models.ManyToManyField(
        "self", related_name="child_batches", symmetrical=False, blank=True
    )
    
    node = models.ForeignKey(
        "supply_chains.Node", on_delete=models.CASCADE, related_name="batches"
    )
    node_wallet = models.ForeignKey(
        "supply_chains.BlockchainWallet",
        on_delete=models.CASCADE,
        related_name="batches",
        null=True,
        blank=True,
        default=None,
    )
    number = models.IntegerField(default=0)
    source_transaction = models.ForeignKey(
        "transactions.Transaction",
        related_name="result_batches",
        default=None,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    name = models.CharField(default="", max_length=800)
    initial_quantity = models.DecimalField(
        default=0.0, max_digits=25, decimal_places=3
    )
    current_quantity = models.DecimalField(
        default=0.0, max_digits=25, decimal_places=3
    )
    unit = models.IntegerField(
        choices=constants.UNIT_CHOICES, default=constants.UNIT_KG
    )
    verified_percentage = models.FloatField(default=0.0)
    type = models.IntegerField(
        choices=constants.BATCH_TYPE_CHOICES,
        default=constants.BATCH_TYPE_SOLID,
    )
    source_type = models.IntegerField(
        default=None, null=True, choices=constants.BATCH_SOURCE_TYPE_CHOICES
    )
    note = models.CharField(max_length=1000, default="", blank=True)

    blockchain_id = models.CharField(
        max_length=200, default="", null=True, blank=True
    )
    blockchain_hash = models.CharField(
        max_length=2000, default="", null=True, blank=True
    )

    info_message_id = models.CharField(default="", max_length=500)
    info_message_address = models.CharField(default="", max_length=500)
    buyer_ref_number = models.CharField(
        max_length=200, default="", null=True, blank=True
    )
    seller_ref_number = models.CharField(
        max_length=200, default="", null=True, blank=True
    )
    external_source = models.CharField(max_length=60, null=True, blank=True)
    external_lat = models.FloatField(default=0.0, null=True, blank=True)
    external_long = models.FloatField(default=0.0, null=True, blank=True)
    archived = models.BooleanField(default=False)
    gtin = models.CharField(max_length=50, blank=True)

    objects = BatchQuerySet.as_manager()

    def __str__(self):
        """Object name in django admin."""
        return "%s %s : %s" % (self.product.name, self.name, self.id)

    @property
    def unit_display(self):
        """unit display."""
        return self.get_unit_display()

    @property
    def wallet_type(self):
        """wallet type."""
        return self.node_wallet.wallet_type

    @property
    def explorer_url(self):
        """Get explorer url."""
        if self.blockchain_hash:
            return settings.HEDERA_TRANSACTION_EXPLORER.format(
                address=self.blockchain_id
            )
        return ""

    @property
    def initial_quantity_in_gram(self):
        """Get initial quantity in grams."""
        return (
            float(self.initial_quantity)
            * constants.UNIT_CONVERSION_FACTOR[self.unit]
        )

    @property
    def initial_quantity_rounded(self):
        """Returns the rounded value of the initial quantity.

        The initial quantity is rounded using the built-in `round()`
        function. The rounded value is based on the current value of the
        `initial_quantity` attribute.
        """
        return round(self.initial_quantity)

    def save(self, *args, **kwargs):
        """Over riding save method to update batch number.

        Batch number is always the django id + 1200
        """
        self.new_instance = not self.pk
        super(Batch, self).save(*args, **kwargs)
        if self.new_instance:
            # map initial farmers
            if self.node.type == NODE_TYPE_FARM:
                self.batch_farmers.model.objects.get_or_create(
                    batch=self, farmer=self.node.farmer
                )
        if not self.number:
            self.number = self.id + 1200
            self.save()

    def update_batch_farmers(self):
        """Function to update batch farmer mapping."""
        if self.node.type == NODE_TYPE_COMPANY:
            # copy inherited farmers.
            if self.parents.exists():
                for batch in self.parents.all():
                    self.batch_farmers.model.objects.copy_farmers(
                        batch, self
                    )

    @property
    def sourced_from(self):
        """get sourced from."""
        return (
            self.source_transaction.supplier
            if self.source_transaction
            else None
        )

    @property
    def destination_wallet(self):
        """Get Destination wallet."""
        if (
            self.source_transaction.transaction_type
            == TRANSACTION_TYPE_INTERNAL
        ):
            return self.node_wallet
        return self.source_transaction.destination_wallet

    @property
    def source_wallet(self):
        """get source wallet."""
        if (
            self.source_transaction.transaction_type
            == TRANSACTION_TYPE_INTERNAL
        ):
            return self.node_wallet
        return self.source_transaction.source_wallet

    @property
    def sourced_by(self):
        """get sourced by."""
        if self.source_transaction:
            if (
                self.source_transaction.transaction_type
                == trans_constants.TRANSACTION_TYPE_EXTERNAL
            ):
                if (
                    self.source_transaction.externaltransaction.type
                    == trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL
                ):
                    return "Returned"
                return "Purchased"
            else:
                if (
                    self.source_transaction.internaltransaction.type
                    == trans_constants.INTERNAL_TRANS_TYPE_MERGE
                ):
                    return "Merged"
                if (
                    self.source_transaction.internaltransaction.type
                    == trans_constants.INTERNAL_TRANS_TYPE_PROCESSING
                ):
                    return "Processed"
        return ""

    @property
    def is_used(self):
        """Is used or not."""
        if self.initial_quantity == self.current_quantity:
            return False
        return True

    def get_source_type(self):
        """Get source type."""
        if self.source_type:
            return self.source_type
        type = None
        if (
            self.source_transaction.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            if (
                self.source_transaction.externaltransaction.type
                == trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL
            ):
                type = constants.BATCH_SOURCE_TYPE_RETURNED
            else:
                type = constants.BATCH_SOURCE_TYPE_RECEIVED
        else:
            if (
                self.source_transaction.internaltransaction.type
                == trans_constants.INTERNAL_TRANS_TYPE_MERGE
            ):
                type = constants.BATCH_SOURCE_TYPE_MERGED
            if (
                self.source_transaction.internaltransaction.type
                == trans_constants.INTERNAL_TRANS_TYPE_PROCESSING
            ):
                type = constants.BATCH_SOURCE_TYPE_PROCESSED
        self.source_type = type
        self.save()
        return type

    def get_parent_actors_levels(self):
        """Get parent actors level."""
        if self.source_transaction:
            return self.source_transaction.get_parent_actors_levels()
        else:
            from v2.supply_chains.models import Node

            return {0: Node.objects.filter(id=self.node.id)}

    def inherit_claims(self):
        """Get inherited claims."""
        from v2.claims.models import AttachedBatchClaim, AttachedBatchCriterion

        for batch in self.source_transaction.source_batches.all():
            for parent_batch_claim in batch.claims.all():
                if (
                    parent_batch_claim.status
                    != claims_constants.STATUS_APPROVED
                ):
                    continue
                (
                    batch_claim,
                    created,
                ) = AttachedBatchClaim.objects.get_or_create(
                    batch=self, claim=parent_batch_claim.claim
                )
                if not created:
                    continue
                batch_claim.attached_from = (
                    claims_constants.ATTACHED_BY_INHERITANCE
                )
                batch_claim.status = claims_constants.STATUS_APPROVED
                batch_claim.verification_percentage = (
                    parent_batch_claim.verification_percentage
                )
                batch_claim.save()

                for (
                    parent_batch_criterion
                ) in parent_batch_claim.criteria.all():
                    (
                        batch_criterion,
                        created,
                    ) = AttachedBatchCriterion.objects.get_or_create(
                        batch_claim=batch_claim,
                        criterion=parent_batch_criterion.criterion,
                    )
                    if not created:
                        continue
                    batch_criterion.attached_from = (
                        claims_constants.ATTACHED_BY_INHERITANCE
                    )
                    batch_criterion.status = parent_batch_criterion.status
                    batch_criterion.verification_info = "Inherited"
                    batch_criterion.save()
                batch_claim.inherit_data()
        return True

    @property
    def owner_id(self):
        """Get owner ID."""
        return self.node_wallet.account_id

    @property
    def quantity(self):
        """Get quantity."""
        return self.initial_quantity_in_gram

    @property
    def token_id(self):
        """Get token ID."""
        return self.product.token_id

    def pre_check(self):
        """Perform pre-check."""
        success, message = super(Batch, self).pre_check()
        if not success:
            return success, message
        if self.blockchain_hash:
            return False, "Hash already exists"
        if self.node.is_company():
            if (
                self.source_transaction and 
                self.source_transaction.transaction_type
                != trans_constants.TRANSACTION_TYPE_INTERNAL
            ):
                self.source_transaction.log_blockchain_transaction()
                return (
                    False,
                    (
                        "Cannot create asset for company, execept for Internal"
                        " transactions"
                    ),
                )
        if not self.node_wallet:
            if not self.node.hedera_wallet:
                self.node.setup_blockchain_account()
                return False, "Blockchain account is not set-up. Setting up"
            self.node_wallet = self.node.blockchain_wallet
            self.save()
        np, c = NodeProduct.objects.get_or_create(
            node_wallet=self.node_wallet, product=self.product
        )
        if not np.associated or not np.kyc_completed:
            np.perform_kyc()
            return False, "KYC not completed. Doing KYC"
        return True, "Pre-check success"

    def create_blockchain_asset(self):
        """Create blockchain asset."""
        if self.blockchain_hash:
            print(
                f"{self} | Blockchain asset already created. Calling"
                " post_success"
            )
            self.post_success()
            return True
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
        """Perform validate callback."""
        if "message" in response:
            if "TOKEN_NOT_ASSOCIATED_TO_ACCOUNT" in response["message"]:
                np, c = NodeProduct.objects.get_or_create(
                    node_wallet=self.node_wallet, product=self.product
                )
                np.associated = False
                np.kyc_completed = False
                np.save()
                np.associate(retry=True)
                return False
            elif "ACCOUNT_KYC_NOT_GRANTED_FOR_TOKEN" in response["message"]:
                np, c = NodeProduct.objects.get_or_create(
                    node_wallet=self.node_wallet, product=self.product
                )
                np.kyc_completed = False
                np.save()
                np.perform_kyc()
                return False
            else:
                capture_message(response["message"])
                return False
        return True

    def update_hash(self, response):
        """Update hash."""
        if not self.validate_callback(response):
            return False
        
        if not response['success']:
            return False

        self.blockchain_hash = response["data"]["transactionHash"]
        self.blockchain_id = response["data"]["transactionId"]
        self.save()
        self.post_success()
        return True

    def post_success(self):
        """Perform post success."""
        self.submit_info_message()
        for tr in self.outgoing_transactions.all():
            tr.log_blockchain_transaction()
        return True

    def message_pre_check(self):
        """perform message pre-check."""
        success, message = super(Batch, self).message_pre_check()
        if not success:
            return success, message
        if not self.blockchain_hash:
            return False, "BC hash exists. Already logged"
        if self.info_message_address:
            return False, "Info hash exists. Already logged"
        return True, "Pre-check success"

    def get_additional_info(self):
        """Get additional info."""
        data = {
            "stock_id": self.number,
            "product_name": self.product.name,
            "quantity": self.initial_quantity,
            "unit": self.unit_display,
            "supply_chain": self.product.supply_chain.name,
            "owner": self.node.full_name,
            "owner_public": self.node_wallet.public,
            "address": self.blockchain_hash,
        }
        return data

    @property
    def topic_id(self):
        """returns topic ID."""
        return settings.HEDERA_TRANSACTION_TOPIC_ID

    @property
    def message(self):
        """get message."""
        return json.dumps(self.get_additional_info(), cls=DjangoJSONEncoder)

    def submit_info_message(self):
        """Get submit info message."""
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

    def migrate_balance_asset(self):
        """Migration balance asset."""
        new_wallet = self.node.blockchain_wallet
        if new_wallet == self.node_wallet:
            print("Node wallet has not changed.")
            return False
        if (
            new_wallet.wallet_type
            != sc_constants.BLOCKCHAIN_WALLET_TYPE_HEDERA
        ):
            print("Can migrate to Hedera only.")
            return False
        if not self.current_quantity > 0:
            print("Batch empty.")
            return False
        migration = BatchMigration.objects.create(
            batch=self,
            old_wallet=self.node_wallet,
            new_wallet=new_wallet,
            migrated_quantity=self.current_quantity,
            unit=self.unit,
            prev_blockchain_id=self.blockchain_id,
            prev_blockchain_hash=self.blockchain_hash,
            prev_info_message_id=self.info_message_id,
            prev_info_message_address=self.info_message_address,
        )
        migration.perform_migration()
        self.save()

        return True

    def get_source_batches(self):
        """Function for get details of source batches when a batch type is
        intermediate.

        is a reverse relation from source_transaction.
        """
        batch = self.source_transaction.source_batches.all()[0]
        return batch.outgoing_transaction_objects.all()[0]


class BatchMigration(
    AbstractBaseModel, AbstractMintedToken, AbstractConsensusMessage
):
    """Model to store data when a batch is migrated to Hedera's blockchain.
    This is used to migrate from topl to hedera as well as when a node wallet
    is reset and the batch balance needs to be moved to the new wallet.

    When a migration is created, the blockchain ID and hash in the existing
    batch will be replaced with the new data and the old data will be stored
    here.

    Attributes:
        batch(obj)      : The batch that is being migrated.
        old_wallet(obj) : The old wallet that had the batch quantity in it.
        new_wallet(obj) : The wallet to which the batch was migrated to.
        migrated_quantity(float)    : The quantity that was migrated.
        unit(choice)    : The unit of quantity that was migrated.

        blockchain_id(str)      : The blockchain ID after migration
        blockchain_hash         : The blockchain hash after migration
        info_message_id         : The message blockchain ID after migration
        info_message_address    : The message blockchain hash after migration

        prev_blockchain_id(str)     : The blockchain ID before migration
        prev_blockchain_hash        : The blockchain hash before migration
        prev_info_message_id        : The message blockchain ID before
                                        migration
        prev_info_message_address   : The message blockchain hash before
                                        migration
    """

    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name="migrations"
    )
    old_wallet = models.ForeignKey(
        "supply_chains.BlockchainWallet",
        on_delete=models.CASCADE,
        related_name="migrations_from",
        null=True,
        blank=True,
        default=None,
    )
    new_wallet = models.ForeignKey(
        "supply_chains.BlockchainWallet",
        on_delete=models.CASCADE,
        related_name="migrations_to",
        null=True,
        blank=True,
        default=None,
    )
    migrated_quantity = models.DecimalField(
        default=0.0, max_digits=25, decimal_places=3
    )
    unit = models.IntegerField(
        choices=constants.UNIT_CHOICES, default=constants.UNIT_KG
    )

    blockchain_id = models.CharField(
        max_length=200, default="", null=True, blank=True
    )
    blockchain_hash = models.CharField(
        max_length=2000, default="", null=True, blank=True
    )

    info_message_id = models.CharField(default="", max_length=500)
    info_message_address = models.CharField(default="", max_length=500)

    prev_blockchain_id = models.CharField(
        max_length=200, default="", null=True, blank=True
    )
    prev_blockchain_hash = models.CharField(
        max_length=2000, default="", null=True, blank=True
    )

    prev_info_message_id = models.CharField(default="", max_length=500)
    prev_info_message_address = models.CharField(default="", max_length=500)

    class Meta:
        """Meta class for the above model."""

        ordering = ("-created_on",)

    def __str__(self):
        """Object name in django admin."""
        return f"Migrated batch - {self.id}"

    @property
    def info_display(self):
        """Get info display."""
        if (
            self.old_wallet.wallet_type
            == sc_constants.BLOCKCHAIN_WALLET_TYPE_TOPL
        ):
            date = datetime.datetime.strftime(self.created_on, "%d %B %Y")
            return f"The stock was migrated from TOPL to HEDERA on {date}."
        return (
            "The wallet was reset resulting in the batch being moved to new"
            " account"
        )

    @property
    def explorer_url(self):
        """Get explorer url."""
        if self.blockchain_hash:
            return settings.HEDERA_TRANSACTION_EXPLORER.format(
                address=self.blockchain_id
            )
        return ""

    @property
    def wallet_type(self):
        """Get wallet type."""
        return self.new_wallet.wallet_type

    @property
    def prev_wallet_type(self):
        """Get previous wallet type."""
        return self.old_wallet.wallet_type

    @property
    def prev_explorer_url(self):
        """Get previous explorer url."""
        if self.prev_blockchain_hash:
            if (
                self.old_wallet.wallet_type
                == sc_constants.BLOCKCHAIN_WALLET_TYPE_HEDERA
            ):
                return settings.HEDERA_TRANSACTION_EXPLORER.format(
                    address=self.prev_blockchain_id
                )
            elif (
                self.old_wallet.wallet_type
                == sc_constants.BLOCKCHAIN_WALLET_TYPE_TOPL
            ):
                return settings.TOPL_TRANSACTION_EXPLORED.format(
                    address=self.prev_blockchain_hash
                )
            else:
                return ""
        return ""

    @property
    def unit_display(self):
        """Get unit display."""
        return self.get_unit_display()

    # @property
    # def explorer_url(self):
    #     if self.blockchain_hash:
    #         return settings.HEDERA_TRANSACTION_EXPLORER.format(
    #             address=self.blockchain_id
    #         )
    #     return ""

    @property
    def quantity_in_gram(self):
        """Get quantity in grams."""
        return (
            float(self.migrated_quantity)
            * constants.UNIT_CONVERSION_FACTOR[self.unit]
        )

    @property
    def owner_id(self):
        """Get Owner ID."""
        return self.new_wallet.account_id

    @property
    def quantity(self):
        """Get quantity."""
        return self.quantity_in_gram

    @property
    def token_id(self):
        """Get token ID."""
        return self.batch.product.token_id

    def pre_check(self):
        """Perform pre-check."""
        success, message = super(BatchMigration, self).pre_check()
        if not success:
            return success, message
        if not self.prev_blockchain_id:
            return False, "Batch has not been logged yet, no need of migration"
        if (
            self.new_wallet.wallet_type
            != sc_constants.BLOCKCHAIN_WALLET_TYPE_HEDERA
        ):
            return False, "Can migrate to Hedera only"
        np, c = NodeProduct.objects.get_or_create(
            node_wallet=self.new_wallet, product=self.batch.product
        )
        if not np.associated or not np.kyc_completed:
            np.perform_kyc()
            return False, "KYC not completed. Doing KYC"
        return True, "Pre-check success"

    def perform_migration(self):
        """Perform migrations."""
        if self.blockchain_hash:
            print(
                f"{self} | Blockchain asset already created. Calling"
                " post_success"
            )
            self.post_success()
            return True

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
        """Validate callback."""
        if "message" in response:
            if "TOKEN_NOT_ASSOCIATED_TO_ACCOUNT" in response["message"]:
                np, c = NodeProduct.objects.get_or_create(
                    node_wallet=self.new_wallet, product=self.batch.product
                )
                np.associated = False
                np.kyc_completed = False
                np.save()
                np.associate(retry=True)
                return False
            elif "ACCOUNT_KYC_NOT_GRANTED_FOR_TOKEN" in response["message"]:
                np, c = NodeProduct.objects.get_or_create(
                    node_wallet=self.new_wallet, product=self.batch.product
                )
                np.kyc_completed = False
                np.save()
                np.perform_kyc()
                return False
            else:
                capture_message(response["message"])
                return False
        return True

    def update_hash(self, response):
        """Update hash."""
        if not self.validate_callback(response):
            return False

        self.blockchain_hash = response["data"]["transactionHash"]
        self.blockchain_id = response["data"]["transactionId"]
        self.save()

        batch = self.batch
        batch.blockchain_hash = response["data"]["transactionHash"]
        batch.blockchain_id = response["data"]["transactionId"]
        batch.save()
        self.post_success()
        return True

    def post_success(self):
        """Do post post_success."""
        b = self.batch
        b.node_wallet = self.new_wallet
        b.save()
        self.submit_info_message()
        return True

    def message_pre_check(self):
        """Do message pre-check."""
        success, message = super(BatchMigration, self).message_pre_check()
        if not success:
            return success, message
        if not self.blockchain_hash:
            return False, "BC hash exists. Already logged"
        if self.info_message_address:
            return False, "Info hash exists. Already logged"
        return True, "Pre-check success"

    def get_additional_info(self):
        """Get additional info."""
        data = {
            "stock_id": self.batch.number,
            "product_name": self.batch.product.name,
            "quantity": self.migrated_quantity,
            "unit": self.unit_display,
            "supply_chain": self.batch.product.supply_chain.name,
            "owner": self.new_wallet.node.full_name,
            "owner_public": self.new_wallet.public,
            "address": self.blockchain_hash,
            "reason": "Batch was migrated to new wallet",
        }
        return data

    @property
    def topic_id(self):
        """get topic ID."""
        return settings.HEDERA_TRANSACTION_TOPIC_ID

    @property
    def message(self):
        """Get message."""
        return json.dumps(self.get_additional_info(), cls=DjangoJSONEncoder)

    def submit_info_message(self):
        """Submit info messages."""
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

        batch = self.batch
        batch.info_message_address = bc_data["transactionHash"]
        batch.info_message_id = bc_data["transactionId"]
        batch.save()
        return True


class BatchFarmerMapping(AbstractBaseModel):
    """Model is to store source farmers of a batch."""

    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name="batch_farmers"
    )
    farmer = models.ForeignKey(
        "supply_chains.Farmer",
        on_delete=models.CASCADE,
        related_name="farmer_batches",
    )

    objects = BatchFarmerMappingQuerySet.as_manager()

    class Meta:
        unique_together = ("batch", "farmer")

    def __str__(self):
        return (
            f"{self.batch.product.name}"
            f"({self.batch.current_quantity}"
            f" {dict(constants.UNIT_CHOICES)[self.batch.unit]}) -"
            f" {self.pk}"
        )
