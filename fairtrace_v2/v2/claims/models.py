"""Models for claims."""
import copy
import json

from common import library as common_lib
from common.library import _get_file_path
from common.models import AbstractBaseModel
from django.conf import settings
from django.contrib.postgres import fields
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.transaction import atomic
from django.utils.crypto import get_random_string
from sentry_sdk import capture_exception
from sentry_sdk import capture_message
from v2.activity import constants as act_constants
from v2.activity.models import Activity
from v2.blockchain.models.submit_message import AbstractConsensusMessage
from v2.communications import constants as notif_constants
from v2.communications.models import Notification
from v2.transactions import constants as trans_constants

from . import constants


# Create your models here.


def get_reference_number():
    """Assign random token to claim ans criterion to identify versions."""
    return get_random_string(16)


class Claim(AbstractBaseModel):
    """Model to store claims. When a claim needs to be updated, a new claim is
    created with an incremented version number and the same reference number.

    Attributes:
        name(char)              : Name of claim.
        description_basic(char) : Basic Description of claim.
        description_full(char)  : Full Description of claim.
        proportional(bool)      : Whether a batch can have the claim partly.
        removable(bool)         : Whether it can removed during transaction
        inheritable(int)        : Whether the batch inherits if transferred/
                                    processed
        verified_by(int)        : Verified by second party or third party.
        type(int)               : User created claim or globally available.
        owners(FKs)             : If a user created claims, which all
                                  companies have access to it.
        supply_chains(FKs)      : Which all supply chains is the claims
                                    available in.
        verifiers(FKs)          : Preset set of verifiers.
        reference(int)          : Reference number to identify multiple
                                  versions of same claim.
        version(int)            : Version number of claim.
        active(bool)            : Whether the claims is active or not. All
                                  previous versions of a claim is made inactive
        latest(bool)            : Whether the claims is the latest or not. Only
                                  one claim with the same reference number will
                                  be the latest.
    """

    name = models.CharField(max_length=500)
    description_basic = models.CharField(
        max_length=500, default="", blank=True
    )
    description_full = models.CharField(
        max_length=2000, default="", blank=True
    )
    type = models.IntegerField(
        choices=constants.CLAIM_TYPE_CHOICES,
        default=constants.CLAIM_TYPE_PRODUCT,
    )

    scope = models.IntegerField(
        choices=constants.CLAIM_SCOPE_CHOICES,
        default=constants.CLAIM_SCOPE_GLOBAL,
    )
    owners = models.ManyToManyField(
        "supply_chains.Node", blank=True, related_name="claims_owned"
    )

    proportional = models.BooleanField(default=True)
    removable = models.BooleanField(default=False)
    inheritable = models.IntegerField(
        default=constants.INHERITANCE_TYPE_NONE,
        choices=constants.INHERITANCE_TYPE_CHOICES,
    )

    verified_by = models.IntegerField(
        default=constants.VERIFIED_BY_THIRD_PARTY,
        choices=constants.VERIFIED_BY_CHOICES,
    )
    supply_chains = models.ManyToManyField(
        "supply_chains.SupplyChain", blank=True
    )

    verifiers = models.ManyToManyField(
        "supply_chains.Node", blank=True, related_name="verifiable_claims"
    )

    reference = models.CharField(default=get_reference_number, max_length=16)
    version = models.IntegerField(default=1)
    active = models.BooleanField(default=True)
    latest = models.BooleanField(default=True)
    image = models.ImageField(
        upload_to=_get_file_path, null=True, default=None, blank=True
    )

    def __str__(self):
        """Object name in django admin."""
        return "%s V%d : %s" % (self.name, self.version, self.id)

    @property
    def lower_name(self):
        """To perform function lower_name."""
        return self.name.lower()

    @atomic()
    def create_new_version(self):
        """Most of the claims details except some minor changes cannot be
        updated, since it might already be attached to some batched.

        If a major change needs to be done, a new version of the claim
        needs to be created. This model method creates a new version of
        the claims with the same details, criterion and fields. This new
        claim can be updated because it won't be attached to any
        batches. The old claims will then be disabled from showing up in
        the interface while adding.
        """
        latest_cl = max(
            [i.version for i in Claim.objects.filter(reference=self.reference)]
        )
        new_claim = copy.deepcopy(self)
        new_claim.id = None
        new_claim.version = latest_cl + 1
        new_claim.save()
        self.active = False
        self.latest = False
        self.save()
        for criterion in self.criteria.all():
            ref = criterion.reference
            latest_cr = max(
                [i.version for i in Criterion.objects.filter(reference=ref)]
            )
            new_criterion = copy.deepcopy(criterion)
            new_criterion.id = None
            new_criterion.version = latest_cr + 1
            new_criterion.claim = new_claim
            new_criterion.save()
            for field in criterion.fields.all():
                new_field = copy.deepcopy(field)
                new_field.criterion = new_criterion
                new_field.id = None
                new_field.save()
        return new_claim


class Criterion(AbstractBaseModel):
    """Model to store claim criterion. When a criterion needs to be updated, a
    new criterion is created with an incremented version number and the same
    reference number.

    Attributes:
        claim(obj)          : Claim that the criterion is associated with.
        name(char)          : Name for the criterion.
        description(char)   : Description for the criterion.
        verification_type(int)  : Verified by system or manually
        verifier(int)       : Choice to map to criterion verification function
        is_mandatory(bool)  : Whether it is a mandatory criterion
        reference(int)      : Reference number to identify multiple versions
                              of same criterion.
        version(int)        : Version number of criterion.
    """

    claim = models.ForeignKey(
        Claim, on_delete=models.CASCADE, related_name="criteria"
    )
    name = models.CharField(default="", max_length=500)
    description = models.TextField(default="", blank=True)
    is_mandatory = models.BooleanField(default=False)

    verification_type = models.IntegerField(
        default=constants.VERIFICATION_TYPE_MANUAL,
        choices=constants.VERIFICATION_TYPE_CHOICES,
    )

    verifier = models.CharField(
        max_length=20,
        default=None,
        null=True,
        blank=True,
        choices=constants.VERIFIER_CHOICES,
    )
    method = models.IntegerField(
        default=None,
        null=True,
        blank=True,
        choices=constants.VERIFICATION_METHOD_CHOICES,
    )

    reference = models.CharField(default=get_reference_number, max_length=16)
    version = models.IntegerField(default=1)

    class Meta:
        verbose_name_plural = "Criteria"

    def __str__(self):
        """Object name in django admin."""
        return "%s - %s : %s" % (self.name, self.claim.name, self.id)

    @property
    def context(self):
        """Mainly used for system claims."""
        if self.verifier in constants.CRITERION_VERIFIERS:
            return constants.CRITERION_VERIFIERS[self.verifier].get_context()
        return {}


class CriterionField(AbstractBaseModel):
    """Field description of an individual field of a form.

    Attributes:
        criteria(obj)           : Criterion for which this data should be
                                  fetched.
        title(char)             : Title of the field.
        description(char)       : Description of the field. Can include
                                  help-text.
        option(char)            : Options that are accepted. For showing in
                                  drop-downs.
        multiple_options(bool)  : Whether multiple options can be accepted.
        type(int)               : Type of field. text/option/file
    """

    criterion = models.ForeignKey(
        Criterion, on_delete=models.CASCADE, related_name="fields"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(default="", blank=True)
    options = models.CharField(
        max_length=1000, default="", blank=True, null=True
    )
    multiple_options = models.BooleanField(default=False)
    type = models.IntegerField(
        choices=constants.FIELD_TYPE_CHOICES, default=constants.FIELD_TYPE_TEXT
    )

    class Meta:
        """Meta class to change ordering."""

        ordering = ("created_on",)

    def __str__(self):
        """Object name in django admin."""
        return "%s: %s" % (self.title, self.id)

    def get_options(self):
        """To perform function get_options."""
        if not self.options:
            return []
        return [i.strip() for i in self.options.split(",")]


class TransactionClaim(AbstractBaseModel):
    """Intermediate model to store what claims were attached to the batch at
    the time of transaction.

    Claims are logically attached to the batch. Therefore, all
    operations are carried out using the AttachedBatchClaim model. This
    TransactionClaim model's sole purpose is to act as a log.
    """

    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.CASCADE,
        related_name="claims",
    )
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE)
    verifier = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.SET_NULL,
        related_name="transactions_verifications",
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        """Object name in django admin."""
        return "%s - %s : %s" % (self.claim.name, self.transaction.id, self.id)

    def log_activity(self):
        """To perform function log_activity."""
        if (
            self.transaction.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            target_node = self.transaction.externaltransaction.destination
        else:
            target_node = self.transaction.internaltransaction.node
        supply_chain = (
            self.transaction.source_batches.first().product.supply_chain
        )
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_ATTACHED_CLAIM_TO_TRANSACTION,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_TRANSACTION_CLAIM,
            node=target_node,
            supply_chain=supply_chain,
            context={"target_name": target_node.full_name},
        )


class AttachedClaim(AbstractBaseModel, AbstractConsensusMessage):
    """Base model for all attached claims, for product claims as well as
    company claims For production claims, the claims will be attached to the
    batch and for company claims, it will be attached to a node."""

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE)
    verifier = models.ForeignKey(
        "supply_chains.Node",
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="claim_verifications",
    )
    attached_by = models.ForeignKey(
        "supply_chains.Node",
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="claims_attached",
    )
    attached_from = models.IntegerField(
        choices=constants.ATTACHED_FROM_CHOICES,
        default=constants.ATTACHED_DIRECTLY,
    )
    status = models.IntegerField(
        choices=constants.STATUS_CHOICES, default=constants.STATUS_PENDING
    )
    note = models.TextField(default="", null=True, blank=True)

    blockchain_id = models.CharField(default="", max_length=500)
    blockchain_address = models.CharField(
        default="", max_length=500, null=True, blank=True
    )

    def __str__(self):
        """To perform function __str__."""
        return f"{self.claim.name} | {self.id}"

    @property
    def supply_chain(self):
        """To perform function supply_chain."""
        if self.claim.type == constants.CLAIM_TYPE_PRODUCT:
            return (
                self.attachedbatchclaim.batch.product.supply_chain
                if hasattr(self, "attachedbatchclaim")
                else None
            )
        else:
            return None

    @property
    def claim_object(self):
        """To perform function claim_object."""
        if self.claim.type == constants.CLAIM_TYPE_PRODUCT:
            return (
                self.attachedbatchclaim
                if hasattr(self, "attachedbatchclaim")
                else None
            )
        else:
            return (
                self.attachedcompanyclaim
                if hasattr(self, "attachedcompanyclaim")
                else None
            )

    def verify(self):
        """To perform function verify."""
        if self.claim_object:
            self.claim_object.verify()

    def log_activity(self):
        """To perform function log_activity."""
        supply_chain = self.supply_chain
        if self.verifier:
            Activity.log(
                event=self,
                activity_type=act_constants.NODE_SENT_VERIFICATION_REQUEST,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
                user=self.creator,
                node=self.attached_by,
                supply_chain=supply_chain,
            )
            Activity.log(
                event=self,
                activity_type=act_constants.NODE_RECEIVED_VERIFICATION_REQUEST,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
                user=self.creator,
                node=self.verifier,
                supply_chain=supply_chain,
            )

    def log_verification_activity(self):
        """To perform function log_verification_activity."""
        supply_chain = self.supply_chain
        if self.status == constants.STATUS_APPROVED:
            self.log_to_blockchain()
            Activity.log(
                event=self,
                activity_type=act_constants.VERIFIER_APPROVED_CLAIM,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
                user=self.creator,
                node=self.verifier,
                supply_chain=supply_chain,
            )
            Activity.log(
                event=self,
                activity_type=act_constants.NODE_CLAIM_APPROVED,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
                user=self.creator,
                node=self.attached_by,
                supply_chain=supply_chain,
            )
        if self.status == constants.STATUS_REJECTED:
            Activity.log(
                event=self,
                activity_type=act_constants.VERIFIER_REJECTED_CLAIM,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
                user=self.creator,
                node=self.verifier,
                supply_chain=supply_chain,
            )
            Activity.log(
                event=self,
                activity_type=act_constants.NODE_CLAIM_REJECTED,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
                user=self.creator,
                node=self.attached_by,
                supply_chain=supply_chain,
            )

    def notify(self):
        """To perform function notify."""
        supply_chain = self.supply_chain
        if not self.verifier:
            return False
        _notify_type = notif_constants.NOTIF_TYPE_RECEIVE_VERIFICATION_REQUEST
        for member in self.verifier.subscribers:
            Notification.notify(
                event=self,
                token=None,
                user=member,
                target_node=self.verifier,
                supply_chain=supply_chain,
                actor_node=self.attached_by,
                notif_type=_notify_type,
            )
        return True

    def notify_verification(self):
        """To perform function notify_verification."""
        supply_chain = self.supply_chain
        if self.status == constants.STATUS_APPROVED:
            n_type = notif_constants.NOTIF_TYPE_APPROVED_CLAIM
        else:
            n_type = notif_constants.NOTIF_TYPE_REJECTED_CLAIM
        for member in self.attached_by.subscribers:
            Notification.notify(
                event=self,
                token=None,
                user=member,
                target_node=self.attached_by,
                supply_chain=supply_chain,
                actor_node=self.verifier,
                notif_type=n_type,
            )
        return True

    def claim_info(self):
        """To perform function claim_info."""
        info = {
            "claim": self.claim.name,
            "claim_id": self.claim.idencode,
            "criteria": [],
        }
        for criterion in self.criteria.all():
            evidences = []
            for resp in criterion.field_responses.all():
                evidence = {"name": resp.field.title}
                if resp.field.type == constants.FIELD_TYPE_FILE:
                    evidence["file_hash"] = resp.file_hash
                else:
                    evidence["value"] = resp.response
                evidences.append(evidence)
            info["criteria"].append(
                {"name": criterion.criterion.name, "data": evidences}
            )
        return info

    @property
    def topic_id(self):
        """To perform function topic_id."""
        return settings.HEDERA_CLAIM_TOPIC_ID

    @property
    def message(self):
        """To perform function message."""
        return json.dumps(
            self.claim_object.claim_info(), cls=DjangoJSONEncoder
        )

    def message_pre_check(self):
        """To perform function message_pre_check."""
        success, message = super(AttachedClaim, self).message_pre_check()
        if not success:
            return success, message

        if self.blockchain_address:
            return False, "Already Logged"
        if self.status != constants.STATUS_APPROVED:
            return False, "Claims is not approved. Cannot be logged"
        if self.blockchain_address:
            return False, "Already logged"
        return True, "Pre-check success"

    def log_to_blockchain(self, user=None):
        """To call request to blockchain node."""
        success, message = self.message_pre_check()
        if not success:
            print(f"{self.__class__.__name__} - {self.id} | {message}")
            return False
        if self.blockchain_id:
            print("Already logged")
            self.post_success()
            return False
        try:
            self.initialize_message(user)
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
        self.save()
        self.post_success()
        return True

    def post_success(self):
        """To perform function post_success."""
        pass
        return True


class AttachedCriterion(AbstractBaseModel):
    """Base model for all attached criterions, both company and product."""

    criterion = models.ForeignKey(
        Criterion, on_delete=models.CASCADE, related_name="attached_criteria"
    )
    attached_from = models.IntegerField(
        choices=constants.ATTACHED_FROM_CHOICES,
        default=constants.ATTACHED_FROM_TRANSACTION,
    )
    status = models.IntegerField(
        choices=constants.STATUS_CHOICES, default=constants.STATUS_PENDING
    )
    blockchain_address = models.CharField(
        default="", max_length=500, null=True, blank=True
    )
    verification_info = models.TextField(default="", blank=True)
    evidence = fields.JSONField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Attached criteria"

    def __str__(self):
        """To perform function __str__."""
        return f"{self.criterion.name} - {self.id}"


class AttachedBatchClaim(AttachedClaim):
    """Model to attached product claims."""

    batch = models.ForeignKey(
        "products.Batch", on_delete=models.CASCADE, related_name="claims"
    )
    verification_percentage = models.FloatField(default=0)

    def __str__(self):
        """Object name in django admin."""
        return "%s - %s : %s" % (self.claim.name, self.batch.id, self.id)

    @property
    def transaction(self):
        """To perform function transaction."""
        if self.attached_from == constants.ATTACHED_FROM_TRANSACTION:
            return self.batch.source_transaction
        return None

    def verify(self):
        """Some claims can be automatically verified.

        If a claims need not be verified by anyone, it's automatically
        marked as verified. If a claims is system verified, the
        particular business logic is computed and the claim is verified
        automatically by the system. System claims cannot be configured
        by Fairfood admin as of now. It needs to be added from the
        developer side.
        """
        if (
            not self.verifier
            and not self.claim.verifiers.exists()
            and self.claim.verified_by == constants.VERIFIED_BY_NONE
        ):
            self.status = constants.STATUS_APPROVED
            self.save()
        for criterion in self.criteria.all():
            criterion.verify()
        if self.attached_from == constants.ATTACHED_BY_INHERITANCE:
            total = 0
            verified = 0
            for (
                batch_obj
            ) in self.batch.source_transaction.source_batch_objects.all():
                total += float(batch_obj.quantity)
                try:
                    batch_claim = batch_obj.batch.claims.get(
                        claim=self.claim, status=constants.STATUS_APPROVED
                    )
                    verified += float(batch_obj.quantity) * (
                        batch_claim.verification_percentage / 100
                    )
                except ObjectDoesNotExist:
                    pass
            self.verification_percentage = common_lib._percentage(
                verified, total
            )
            self.save()
        else:
            self.check_and_approve()

    def check_and_approve(self):
        """To mark as approved if all criterions are approved."""
        criteria_status = list(
            set([cri.status for cri in self.criteria.all()])
        )
        if len(criteria_status) == 1:
            self.status = criteria_status[0]
            if criteria_status[0] == constants.STATUS_APPROVED:
                self.verification_percentage = 100
            self.save()

    def inherit_data(self):
        """To inherit data from source batches if the claim is attached by
        inheritance."""
        if self.attached_from != constants.ATTACHED_BY_INHERITANCE:
            return None
        for criterion in self.criteria.all():
            criterion.inherit_data()
        source_batches = self.batch.source_transaction.source_batches.filter(
            claims__claim=self.claim
        )
        statuses = [
            bc.status
            for bc in AttachedBatchClaim.objects.filter(
                batch__in=source_batches, claim=self.claim
            )
        ]
        if len(set(statuses)) == 1:
            self.status = statuses[0]
        else:
            self.status = constants.STATUS_PARTIAL
            capture_message(
                f"Something wrong with batch claim {self.id}. Status are"
                f" {statuses}."
            )
        self.save()

    def log_activity(self):
        """Log activity in node profile."""
        supply_chain = self.batch.product.supply_chain
        if self.attached_from == constants.ATTACHED_DIRECTLY:
            Activity.log(
                event=self,
                activity_type=act_constants.NODE_USER_ATTACHED_CLAIM_TO_BATCH,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
                user=self.creator,
                node=self.batch.node,
                supply_chain=supply_chain,
            )
        super(AttachedBatchClaim, self).log_activity()

    def get_evidence(self):
        """Get evidence data."""
        evidences = []
        for criterion in self.criteria.all():
            if criterion.evidence:
                evidences.append(criterion.evidence)
        return evidences

    def inheritable(self, product):
        """Check if an attached claim is inheritable."""
        if self.claim.inheritable == constants.INHERITANCE_TYPE_ALL:
            return True
        if self.claim.inheritable == constants.INHERITANCE_TYPE_NONE:
            return False
        if self.batch.product == product:
            return True

    def claim_info(self):
        """Additional info that is to be logged into blockchain."""
        info = super(AttachedBatchClaim, self).claim_info()

        info["owner_id"] = self.batch.node.idencode
        info["owner_name"] = self.batch.node.full_name
        info["stock_id"] = self.batch.number
        info["product_name"] = self.batch.product.name
        info["supply_chain"] = self.batch.product.supply_chain.name

        return info


class AttachedBatchCriterion(AttachedCriterion):
    """Model for attaching critetion to batch through attached batch claim."""

    batch_claim = models.ForeignKey(
        AttachedBatchClaim, on_delete=models.CASCADE, related_name="criteria"
    )

    class Meta:
        verbose_name_plural = "Attached batch criteria"

    def __str__(self):
        """Object name in django admin."""
        return "%s - %s : %s" % (
            self.batch_claim.claim.name,
            self.batch_claim.batch.id,
            self.id,
        )

    def inherit_data(self):
        """To inherit data from source batches if the claim is attached by
        inheritance."""
        sbs = self.batch_claim.batch.source_transaction.source_batches.filter(
            claims__claim=self.batch_claim.claim
        )
        _f_dict = {
            "criterion__criterion": self.criterion,
            "criterion__attachedbatchcriterion__batch_claim__batch__in": sbs,
        }
        for field_response in FieldResponse.objects.filter(**_f_dict):
            file_exists = self.field_responses.filter(
                field=field_response.field,
                response=field_response.response,
                file_hash=field_response.file_hash,
                added_by=field_response.added_by,
            ).exists()

            if (
                field_response.file_hash or field_response.response
            ) and not file_exists:
                field_response.id = None
                field_response.criterion = self
                field_response.save()
        self.verify()

    def verify(self):
        """if a claims is a system claims, the business logic is run to verify
        the claims.

        Otherwise is a batch claim is approved by the vrifier, all sub
        criterions are marked as approved.
        """
        if (
            self.criterion.verification_type
            == constants.VERIFICATION_TYPE_SYSTEM
        ):
            verifier = constants.CRITERION_VERIFIERS[self.criterion.verifier]()
            status, info, evidence = verifier.verify(self)
            self.status = (
                constants.STATUS_APPROVED
                if status
                else constants.STATUS_REJECTED
            )
            self.verification_info = info
            self.evidence = evidence
            self.save()
            self.batch_claim.check_and_approve()
        else:
            if self.batch_claim.status == constants.STATUS_APPROVED:
                self.status = constants.STATUS_APPROVED
                self.save()
            if self.batch_claim.status == constants.STATUS_REJECTED:
                self.status = constants.STATUS_REJECTED
                self.save()

    def approve(self):
        """To approve criterion."""
        self.status = constants.STATUS_APPROVED
        self.save()
        self.batch_claim.check_and_approve()


class AttachedCompanyClaim(AttachedClaim):
    """Model to store company claims.

    Inherited from AttachedClaims model
    """

    node = models.ForeignKey(
        "supply_chains.Node",
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="claims",
    )

    def __str__(self):
        """To perform function __str__."""
        return f"{self.claim.name} - {self.node.full_name} | {self.id}"

    def log_activity(self):
        """To perform function log_activity."""
        Activity.log(
            event=self,
            activity_type=act_constants.NODE_ADDED_COMPANY_CLAIM,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
            user=self.creator,
            node=self.node,
        )
        super(AttachedCompanyClaim, self).log_activity()

    def verify(self):
        """To perform function verify."""
        if self.claim.scope == constants.CLAIM_SCOPE_LOCAL:
            self._approve()
            return True
        if not self.claim.verifiers.all():
            self._approve()
            return True
        return False

    def _approve(self):
        """To perform function _approve."""
        for cr in self.criteria.all():
            cr.approve()
        self.status = constants.STATUS_APPROVED
        self.save()
        self.node.update_cache()
        return True

    def claim_info(self):
        """To perform function claim_info."""
        info = super(AttachedCompanyClaim, self).claim_info()

        info["node_id"] = self.node.idencode
        info["node_name"] = self.node.full_name

        return info


class AttachedCompanyCriterion(AttachedCriterion):
    """Model to store company claim criterion.

    Not exactly required for company claims, the criterion will be the
    same as claim
    """

    company_claim = models.ForeignKey(
        AttachedCompanyClaim, on_delete=models.CASCADE, related_name="criteria"
    )

    def __str__(self):
        """To perform function __str__."""
        return (
            f"{self.criterion.name} - {self.company_claim.node.full_name} |"
            f" {self.id}"
        )

    def approve(self):
        """To perform function approve."""
        self.status = constants.STATUS_APPROVED
        self.save()


class FieldResponse(AbstractBaseModel):
    """Model to store form response.

    Attributes:
        criterion(obj)  : Criterion for which the response was recorded.
        field(obj)      : Field for which the response was recorded.
        response(char)  : Response for the field if it is a char response.
        file(file)     : File field if its a file response.
    """

    criterion = models.ForeignKey(
        AttachedCriterion,
        on_delete=models.CASCADE,
        related_name="field_responses",
        null=True,
    )

    field = models.ForeignKey(CriterionField, on_delete=models.CASCADE)
    response = models.CharField(max_length=1000)
    file = models.FileField(
        upload_to=_get_file_path, null=True, default=None, blank=True
    )
    file_hash = models.CharField(max_length=500, null=True, blank=True)
    added_by = models.ForeignKey(
        "supply_chains.Node", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        """Object name in django admin."""
        return "%s : %s" % (self.field.title, self.id)

    @property
    def file_url(self):
        """Get file url."""
        if self.file:
            return self.file.url
        return None

    def get_response(self):
        """To perform function get_response."""
        if self.field.type == constants.FIELD_TYPE_FILE:
            return self.file_url
        return self.response


class ClaimComment(AbstractBaseModel):
    """Model to store messages send by claimant and verifier in claims
    verification."""

    sender = models.ForeignKey(
        "supply_chains.Node", on_delete=models.SET_NULL, null=True, blank=True
    )
    message = models.TextField(default="", null=True, blank=True)
    attached_claim = models.ForeignKey(
        AttachedClaim,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )

    def __str__(self):
        """To perform function __str__."""
        return f"Sent by {self.sender.full_name}."

    def log_activity(self):
        """To perform function log_activity."""
        # batch_claim = self.attached_claim.attachedbatchclaim
        if self.attached_claim.claim.type == constants.CLAIM_TYPE_PRODUCT:
            _product = (
                self.attached_claim.attachedbatchclaim.batch.product
                if hasattr(self.attached_claim, "attachedbatchclaim")
                else None
            )
            sc = _product.supply_chain if _product else None
            supply_chain = sc
        else:
            supply_chain = None
        if self.attached_claim.verifier == self.sender:
            receivers = [self.attached_claim.attached_by]
        elif self.attached_claim.attached_by == self.sender:
            receivers = [self.attached_claim.verifier]
        else:
            receivers = [
                self.attached_claim.verifier,
                self.attached_claim.attached_by,
            ]
        Activity.log(
            event=self,
            activity_type=act_constants.SENT_COMMENT_ON_CLAIM,
            object_id=self.id,
            object_type=act_constants.OBJECT_TYPE_CLAIM_COMMENT,
            user=self.creator,
            node=self.sender,
            supply_chain=supply_chain,
        )
        for receiver in receivers:
            if receiver == self.sender:
                continue
            if not receiver:
                continue
            Activity.log(
                event=self,
                activity_type=act_constants.RECEIVED_COMMENT_ON_CLAIM,
                object_id=self.id,
                object_type=act_constants.OBJECT_TYPE_CLAIM_COMMENT,
                user=self.creator,
                node=receiver,
                supply_chain=supply_chain,
            )
            context = {"verification_id": self.attached_claim.idencode}
            for member in receiver.subscribers:
                Notification.notify(
                    event=self,
                    token=None,
                    user=member,
                    target_node=receiver,
                    supply_chain=supply_chain,
                    actor_node=self.sender,
                    notif_type=notif_constants.NOTIF_TYPE_CLAIM_COMMENT,
                    context=context,
                )
