import abc
import itertools
import operator
from abc import abstractmethod
from collections import defaultdict

from common import library
from common.cache import filesystem_cache
from common.exceptions import BadRequest
from django.conf import settings
from django.db.models import Case
from django.db.models import CharField
from django.db.models import F, IntegerField
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Subquery
from django.db.models import Sum
from django.db.models import Value
from django.db.models import When
from django.db.models.functions import Concat, Left
from django.template import Context
from django.template import Template
from django.utils import translation
from v2.claims import constants as claim_const
from v2.claims.models import AttachedBatchClaim, AttachedClaim, \
    AttachedCompanyClaim
from v2.claims.models import AttachedBatchCriterion
from v2.claims.models import FieldResponse
from v2.dashboard.models import ConsumerInterfaceActor
from v2.dashboard.models import ConsumerInterfaceProduct
from v2.dashboard.models import ConsumerInterfaceStage
from v2.dashboard.models import ProgramStat
from v2.products import constants as prod_const
from v2.products.constants import INCOMING
from v2.products.constants import INCOMING_DESCRIPTION
from v2.products.constants import OUTGOING
from v2.products.constants import OUTGOING_DESCRIPTION
from v2.products.constants import PROCESSED
from v2.products.constants import PROCESSED_DESCRIPTION
from v2.products.models import Batch, Product
from v2.supply_chains import constants as sup_const
from v2.supply_chains.constants import NODE_TYPE_FARM, GRANTED
from v2.supply_chains.models import BlockchainWallet
from v2.supply_chains.models import Company
from v2.supply_chains.models import Node
from v2.supply_chains.models import Operation
from v2.transactions import constants as txn_const
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import SourceBatch
from v2.transactions.models import Transaction


class AbstractTraceSerializer(metaclass=abc.ABCMeta):
    """Abstract base serializer class for new storytelling interface apis."""

    def __init__(self, instance, theme, *args, context=None):
        """To perform function __init__."""

        self.instance = instance
        self.theme = theme
        self._check_theme()
        if context and "view" in context:
            klass_name = context.get("view").__class__.__name__
            # Setting language en of reports
            if "ForReport" in klass_name:
                translation.activate("en")
        else:
            self.theme.check_language_rollback()
        self.args = args

    def _check_theme(self):
        """check theme is compatible with the batch."""
        if not self.theme.is_public:
            batch_chain = self.instance.node.get_chain(
                supply_chain=self.instance.product.supply_chain,
                include_self=True,
            ).values_list("id", flat=True)
            if self.instance.node_id not in batch_chain:
                raise BadRequest("Batch cannot be traced with this theme")

    def parent_transactions(self):
        """Force evaluating and start new lazy queryset for reduce query
        complexity."""
        # create key with language
        lan = translation.get_language()
        key = (
            f"{self.instance.source_transaction.id}"
            f"_parent_transactions"
            f"_{lan}"
        )

        # get cached transactions if any.
        cached_parent_transaction = filesystem_cache.get(key)
        if cached_parent_transaction is not None:
            return cached_parent_transaction
        source_transaction = self.instance.source_transaction
        if source_transaction.result_batches.count() > 1:
            parent_transactions = source_transaction.get_parent_transactions(
                batches=Batch.objects.filter(pk=self.instance.pk))
        else:
            parent_transactions = source_transaction.get_parent_transactions()
        transactions_ids = parent_transactions.values_list("id", flat=True)
        translations = Transaction.objects.filter(
            pk__in=list(transactions_ids)
        )

        # Caching transactions
        filesystem_cache.set(key, translations)
        return translations

    @staticmethod
    def involved_actors(transactions):
        """Get actor queryset."""
        # separated transaction with type
        external_transaction_actor_ids = list(
            itertools.chain(
                *transactions.filter(
                    transaction_type=txn_const.TRANSACTION_TYPE_EXTERNAL
                ).values_list(
                    "externaltransaction__source_id",
                    "externaltransaction__destination_id",
                )
            )
        )
        internal_transaction_transaction_actor_ids = list(
            transactions.filter(
                transaction_type=txn_const.TRANSACTION_TYPE_INTERNAL,
                internaltransaction__mode=txn_const.TRANSACTION_MODE_MANUAL,
            ).values_list("internaltransaction__node_id", flat=True)
        )

        # filter involved actors
        return Node.objects.filter(
            pk__in=(
                    external_transaction_actor_ids
                    + internal_transaction_transaction_actor_ids
            )
        ).prefetch_related(
            "outgoing_transactions",
            "incoming_transactions",
            "internaltransactions",
        )

    @property
    @abstractmethod
    def data(self):
        """To perform function ata."""
        raise NotImplementedError("`get_data()` must be implemented.")


class TraceClaimsWithBatchSerializer(AbstractTraceSerializer):
    """Trace and serialize the claims with Batch instance."""

    @property
    def data(self):
        """To perform function ata."""
        return self.get_claims()

    def get_claims(self) -> list:
        """Main method to called to get traced claims data."""

        transactions = (
            self.instance.source_transaction.get_parent_transactions()
        )

        transaction_ids = transactions.values_list("id", flat=True)

        # Getting batch attached claim ids
        attached_claim_ids = list(
            self.instance.claims.filter(
                attached_from=claim_const.ATTACHED_DIRECTLY,
                status=claim_const.STATUS_APPROVED,
            ).values_list("claim_id")
        )

        # Getting batch node attached company claim ids
        attached_company_claim_ids = list(
            AttachedCompanyClaim.objects.filter(
                node__in=self.involved_actors(transactions)
            ).values_list("claim_id"))

        # pair-up claim and transactions (for batch claims transaction is None)
        attached_claim_ids = list(
            map(lambda _claim: (*_claim, None), attached_claim_ids)
        )
        attached_company_claim_ids = list(
            map(lambda _claim: (*_claim, None), attached_company_claim_ids)
        )

        # Getting transaction related attached claims
        transaction_claims = (
            AttachedBatchClaim.objects.filter(
                batch__source_transaction__in=transaction_ids,
                attached_from__in=[
                    claim_const.ATTACHED_FROM_TRANSACTION,
                    claim_const.ATTACHED_BY_INHERITANCE,
                ],
                status=claim_const.STATUS_APPROVED,
            )
            .annotate(transactions_id=F("batch__source_transaction_id"))
            .values_list("claim_id", "transactions_id")
        )

        # mapping claims with transaction_id also remove duplicated.
        claim_transactions = dict((
            *attached_claim_ids,
            *transaction_claims,
            *attached_company_claim_ids))

        claim_data = self.get_claims_data(claim_transactions.keys())
        transaction_data = self.get_claim_transaction_data(
            claim_transactions.values()
        )

        processed_claim = []
        data = []
        for claim in claim_data.iterator():
            if claim["claim_id"] not in processed_claim:

                if not claim_transactions[claim["claim_id"]]:
                    claim["transaction_data"] = self._set_transaction_data()
                else:
                    claim["transaction_data"] = transaction_data[
                        claim_transactions[claim["claim_id"]]
                    ]

                processed_claim.append(claim["claim_id"])

                # setting primary claim
                if (
                        self.theme
                        and self.theme.default_claim_id == claim["claim_id"]
                ):
                    claim["primary_claim"] = True
                else:
                    claim["primary_claim"] = False

                # adding theme_image to show theme images.
                claim["theme_image"] = None
                claim["external_link"] = None
                claim["interventions"] = []

                if self.theme:
                    self._set_theme_params(claim)

                claim["type"] = (
                    "COMPANY_CLAIM"
                    if claim["claim_id"]
                    in dict(attached_company_claim_ids).keys()
                    else "BATCH_CLAIM")

                claim["claim_id"] = library.encode(claim["claim_id"])
                batch_claim_id = claim.pop("id")
                claim["evidences"] = list(self._get_evidences(batch_claim_id))
                method, context = self._get_context_method(batch_claim_id)
                claim["method"] = method
                claim["context"] = context

                data.append(claim)

        return data

    @staticmethod
    def get_claims_data(claim_ids):
        """Get and convert claims to values."""
        lan = translation.get_language().split("-")[0]
        claim_annotations = {
            "name": F(f"claim__name_{lan}"),
            "description_basic": F(f"claim__description_basic_{lan}"),
            "description_full": F(f"claim__description_full_{lan}"),
            "image_url": Case(
                When(Q(Q(claim__image__isnull=False)| ~Q(claim__image="")),
                     then=Concat(Value("https:"), Value(settings.MEDIA_URL), 
                                 F("claim__image"))),
                output_field=CharField(),
                default=Value(""),
            ),
        }
        claim_values = (
            "id",
            "claim_id",
            "name",
            "description_basic",
            "description_full",
            "attached_from",
            "status",
            "blockchain_address",
            "image_url",
        )

        return (
            AttachedClaim.objects.filter(claim_id__in=claim_ids)
            .annotate(**claim_annotations)
            .values(*claim_values)
        )

    @staticmethod
    def get_claim_transaction_data(parent_transaction_ids):
        """Get and convert transactions to values amd map with ids."""

        data = {}
        transactions = Transaction.objects.filter(
            pk__in=parent_transaction_ids
        )

        # Getting all wallet ids from the transactions.
        wallets_ids = list(
            itertools.chain(
                *transactions.filter(
                    transaction_type=txn_const.TRANSACTION_TYPE_EXTERNAL
                ).values_list(
                    "externaltransaction__destination_wallet_id",
                    "externaltransaction__source_wallet_id",
                )
            )
        )
        wallets_ids += list(
            transactions.filter(
                transaction_type=txn_const.TRANSACTION_TYPE_INTERNAL
            ).values_list("internaltransaction__node_wallet", flat=True)
        )

        mapped_wallets = get_mapped_wallets(wallets_ids)

        for transaction in transactions.iterator():
            item = {
                "date": transaction.date.timestamp(),
                "product_name": transaction.product.name,
                "source_name": transaction.source.full_name,
                "source_id": transaction.source.idencode,
                "destination_name": transaction.destination.full_name,
                "destination_id": transaction.destination.idencode,
                "quantity": transaction.destination_quantity,
                "source_wallet": mapped_wallets[transaction.source_wallet.id],
                "destination_wallet": mapped_wallets[
                    transaction.destination_wallet.id
                ],
                "blockchain_address": transaction.blockchain_address,
                "explorer_url": transaction.explorer_url,
                "wallet_type": transaction.wallet_type,
            }
            data[transaction.id] = item
        return data

    def _set_transaction_data(self):
        """Constructing the transaction data from the batch instance."""
        theme_product = ConsumerInterfaceProduct.objects.filter(
            theme=self.theme, product=self.instance.product).first()
        wallet_data = {
            "id": "",
            "account_id": "",
            "public": "",
            "wallet_type": "",
            "explorer_url": "",
        }
        transaction_data = {
            "date": self.instance.created_on.timestamp(),
            "product_name": (theme_product.name
                             if theme_product
                             else self.instance.product.name),
            "source_name": self.instance.node.full_name,
            "source_id": self.instance.node.idencode,
            "destination_name": self.instance.node.full_name,
            "destination_id": self.instance.node.idencode,
            "quantity": self.instance.initial_quantity,
            "wallet_type": "",
            "explorer_url": "",
        }

        if self.instance.node_wallet:
            transaction_data.update(
                {
                    "wallet_type": self.instance.node_wallet.wallet_type,
                    "explorer_url": self.instance.node_wallet.explorer_url,
                    "blockchain_address": "",
                }
            )

        source_wallet = wallet_data.copy()
        if self.instance.source_wallet:
            source_wallet["id"] = self.instance.source_wallet.id
            source_wallet[
                "account_id"
            ] = self.instance.source_wallet.account_id
            source_wallet["public"] = self.instance.source_wallet.public
            source_wallet[
                "wallet_type"
            ] = self.instance.source_wallet.wallet_type
            source_wallet[
                "explorer_url"
            ] = self.instance.source_wallet.explorer_url
        transaction_data["source_wallet"] = source_wallet

        destination_wallet = wallet_data.copy()
        if self.instance.destination_wallet:
            destination_wallet["id"] = self.instance.destination_wallet.id
            destination_wallet[
                "account_id"
            ] = self.instance.destination_wallet.account_id
            destination_wallet[
                "public"
            ] = self.instance.destination_wallet.public
            destination_wallet[
                "wallet_type"
            ] = self.instance.destination_wallet.wallet_type
            destination_wallet[
                "explorer_url"
            ] = self.instance.destination_wallet.explorer_url
        transaction_data["destination_wallet"] = destination_wallet
        return transaction_data

    @staticmethod
    def _get_evidences(claim_id):
        """To perform function _get_evidences."""
        evidences = defaultdict(list)
        file_response = (
            FieldResponse.objects.filter(
                criterion__attachedbatchcriterion__batch_claim_id=claim_id
            )
            .annotate(
                title=F("field__title"),
                type=F("field__type"),
                res=F("response"),
            )
            .values("field_id", "title", "res", "file", "type", "added_by")
        )
        list(
            map(
                lambda response: response.update(
                    {
                        "file": settings.MEDIA_URL + response.pop("file"),
                        "field_id": library._encode(response.pop("field_id")),
                    }
                ),
                file_response,
            )
        )
        list(
            map(
                lambda response: evidences[response.pop("added_by")].append(
                    response
                ),
                file_response,
            )
        )
        company_data = Company.objects.filter(pk__in=evidences.keys()).values(
            "id", "name"
        )
        added_by_data_map = dict(map(lambda c: (c.pop("id"), c), company_data))
        return map(
            lambda e: {"added_by": added_by_data_map[e[0]], "data": e[1]},
            evidences.items(),
        )

    @staticmethod
    def _get_context_method(claim_id):
        """To perform function _get_context_method."""
        attached_criteria = AttachedBatchCriterion.objects.filter(
            batch_claim_id=claim_id
        )
        method = 0
        context = []
        for criterion in attached_criteria.iterator():
            _criterion = criterion.criterion
            if _criterion.method:
                method = _criterion.method
            if _criterion.context:
                context.append(_criterion.context)
        return method, context

    def _set_theme_params(self, claim):
        """Set additional parameters for a claim based on the associated theme.

        This method takes a claim dictionary as input and retrieves the
        theme-specific claim associated with the claim's claim_id. If a
        theme-specific claim exists, it updates the claim dictionary with the
        description_full and theme_image values based on the theme-specific
        claim. If the theme-specific claim does not exist or the
        description_full value is already present in the claim dictionary, no
        changes are made.

        Args:
            claim (dict): The claim dictionary.
        """
        claim_id = claim["claim_id"]

        theme_claim = self.theme.claims.filter(claim_id=claim_id).first()
        if theme_claim:
            claim["description_full"] = (
                theme_claim.description
                if theme_claim.description
                else claim["description_full"]
            )
            claim["theme_image"] = theme_claim.image_url
            claim["external_link"] = theme_claim.external_link

            for intervention in theme_claim.interventions.all():
                intervention_data = {
                    "id": library.encode(intervention.id),
                    "name": intervention.name,
                    "description": intervention.description,
                    "image_url": intervention.image_url,
                    "external_link": intervention.external_link
                }
                claim["interventions"].append(intervention_data)


class TraceMapSerializer(AbstractTraceSerializer):
    """Class to handle TraceMapSerializer and functions."""

    @property
    def data(self):
        """To perform function ata."""
        return {"map": self.get_map(), "program": self.get_program()}

    def get_map(self):
        """Get actors list with mapped actor ids."""
        actors_values_fields = ("id", "name", "longitude", "latitude")
        actors_annotate_fields = self._get_actors_annotations()

        transactions = self.parent_transactions()
        actors = self.involved_actors(transactions)
        actors = actors.annotate(**actors_annotate_fields).values(
            *actors_values_fields
        )
        actors = list(actors)
        connected_node_data = self._get_node_pairs(transactions)
        external_batch_data = self._get_batch_data(transactions)
        self.add_external_batches(external_batch_data, actors)
        for actor in actors:
            # Batch IDs are prefixed with EX so that they can be distinguished.
            # they cannot be encoded.
            _id = library._encode(actor["id"])
            if not _id:
                continue
            actor["id"] =_id
            actor["connected_to"] = connected_node_data[actor["id"]]
            actor["external_source"] = False
        return actors

    def get_program(self):
        """To perform function get_program."""
        program_details = {}
        if self.theme and self.theme.program:
            program_details["id"] = self.theme.program.idencode
            program_details["tittle"] = self.theme.program.title
            program_details["description"] = self.theme.program.description
            stats = ProgramStat.objects.filter(program=self.theme.program.id)
            program_details["program_stats_details"] = stats.values(
                "name", "value", "is_visible", "symbol"
            )
        return program_details
    
    def add_external_batches(self, external_batch_data, actors):
        """To perform function add_external_batches."""
        for batch in external_batch_data:
            batch_to_actor = {
                    "id": "EX" + library._encode(batch["batch__id"]),
                    "name": batch["batch__name"],
                    "connected_to": [library._encode(
                        batch[
                            "source_id"
                            ])],
                    "latitude": batch["batch__external_lat"],
                    "longitude": batch["batch__external_long"],
                    "external_source": True
            }
            actors.append(batch_to_actor)

    def _get_batch_data(self, transactions):
        """To perform function _get_batch_data."""
        internal_transactions = (
            self.instance.source_transaction.get_parent_transactions(
                only_internal=True
            )
        )
        source_batches = SourceBatch.objects.filter(
            Q(transaction__in=transactions)
            | Q(transaction__in=internal_transactions),
            batch__external_source__isnull=False,
            batch__node__isnull=False,
        ).annotate(source_id=Case(
            When(transaction__internaltransaction__isnull=False, 
                 then="transaction__internaltransaction__node_id"), 
            default="transaction__externaltransaction__source_id",
            output_field=IntegerField()
        )).values(
            "batch__id", "batch__name", "batch__external_lat", 
            "batch__external_long", "source_id")
        return source_batches
        
        


    @staticmethod
    def _get_node_pairs(transactions):
        """
        creating a key value pair for every connection and group them
        with key
        eg:
            {
                'sas' : ['asd', 'sds', 'dad'],
                'dda' : ['asd', 'das', 'dad'],

            }
        """

        # source to destination connection
        external_pairs = list(
            transactions.filter(
                transaction_type=txn_const.TRANSACTION_TYPE_EXTERNAL
            ).values_list(
                "externaltransaction__source_id",
                "externaltransaction__destination_id",
            )
        )

        # destination to source connection
        external_pairs_swap = list(map(lambda x: (x[1], x[0]), external_pairs))

        # self node to node connection
        internal_pairs = list(
            transactions.filter(
                transaction_type=txn_const.TRANSACTION_TYPE_INTERNAL
            )
            .annotate(destination_id=F("internaltransaction__node_id"))
            .values_list("internaltransaction__node_id", "destination_id")
        )

        combined = itertools.groupby(
            external_pairs + external_pairs_swap + internal_pairs,
            operator.itemgetter(0),
        )
        data = defaultdict(list)
        for key, values in combined:
            data[library.encode(key)].extend(
                [library.encode(v[1]) for v in values]
            )
        return data

    @staticmethod
    def _get_actors_annotations():
        """To perform function _get_actors_annotations."""
        return {
            "name": Case(
                When(type=sup_const.NODE_TYPE_COMPANY, then="company__name"),
                When(
                    type=sup_const.NODE_TYPE_FARM,
                    farmer__consent_status=sup_const.GRANTED,
                    then=Concat("farmer__first_name", "farmer__last_name"),
                ),
                default=Value("Anonymous"),
                output_field=CharField(),
            )
        }


class TraceStagesWithBatchSerializer(AbstractTraceSerializer):
    """Class to handle TraceStagesWithBatchSerializer and functions."""

    @property
    def data(self):
        """To perform function ata."""
        return self.get_stages()

    def get_stages(self):
        """To perform function get_stages."""
        data = []
        transactions = self.parent_transactions()
        actors = self._get_actors(transactions)

        stage_actors_dict = self.instance.get_parent_actors_levels()
        for stage in sorted(stage_actors_dict.keys(), reverse=True):
            stage_actors_query_set = stage_actors_dict[stage]
            stage_actors_ids = [
                library.encode(_actor_id)
                for _actor_id in stage_actors_query_set.order_by(
                    "-image"
                ).values_list("id", flat=True)
            ]
            filtered_stage_actors = list(filter(
                lambda a: a in actors, stage_actors_ids))
            # get actors in the stage
            stage_actors = list(
                map(lambda a: actors[a], filtered_stage_actors))

            # get product names from actors and remove duplicates.
            stage_product_data = list(itertools.chain(
                *map(lambda p: p["products"], stage_actors)
            ))

            stage_products = set(map(lambda p: p["name"], stage_product_data))
            stage_theme_products = set(
                map(lambda p: p["theme_name"], stage_product_data)
            )
            operations = set(
                map(lambda op: op["primary_operation"], stage_actors)
            )

            external_sources = [
                dict(
                    node=i["id"],
                    node_name=i["name"],
                    external_sources=i["external_sources"],
                )
                for i in stage_actors
                if i["external_sources"]
            ]

            title = library._list_to_sentence(operations)
            image = None
            if (
                    self.theme
                    and self.theme.stages.filter(
                operation__name__in=operations
            ).exists()
            ):
                stage = self.theme.stages.filter(
                    operation__name__in=operations
                ).first()
                actor_name = stage.actor_name
                image = stage.image_url
                title = stage.title
            elif len(stage_actors) == 1:
                actor_name = stage_actors[0]["name"]
                operation = Operation.objects.filter(
                    name__icontains=stage_actors[0]["primary_operation"]
                )
                if operation.exists() and operation.first().image:
                    image = operation.first().image.url
            else:
                actor_name = (
                    f"{len(stage_actors)}"
                    f' {stage_actors[0]["primary_operation"]}s'
                )

            data.append(
                {
                    "actors": stage_actors,
                    "stage_products": (
                        stage_theme_products
                        if any(stage_theme_products)
                        else stage_products
                    ),
                    "tittle": title,
                    "image": image,
                    "actor_name": actor_name,
                    "external_sources": external_sources,
                }
            )
        return data

    def _get_actors(self, transactions) -> dict:
        actors_values_fields = (
            "id",
            "name",
            "longitude",
            "latitude",
            "description_basic",
            "province",
            "country",
            "status",
            "supply_chains",
            "transaction_quantity",
            "image_url",
            "type",
        )
        actors_annotate_fields = self._get_actors_annotations(transactions)

        source_transaction = self.instance.source_transaction
        actors = self.involved_actors(transactions)

        # fetch and annotate with required values
        actors = actors.annotate(**actors_annotate_fields).values(
            *actors_values_fields
        )
        actors = list(actors.iterator())
        external_sources = self._get_external_sources(transactions)
        self._actor_data(
            actors, source_transaction, transactions, external_sources
        )
        return dict(map(lambda a: (a["id"], a), actors))

    @staticmethod
    def _get_actors_annotations(transactions: QuerySet) -> dict:
        """Create annotation fields for actors."""
        out_going_quantity = ExternalTransaction.objects.filter(
            source_id=OuterRef("pk"), id__in=transactions
        ).annotate(quantity=Sum("_source_quantity"))
        return {
            "name": Case(
                When(type=sup_const.NODE_TYPE_COMPANY, then="company__name"),
                When(
                    type=sup_const.NODE_TYPE_FARM,
                    farmer__consent_status=sup_const.GRANTED,
                    then=Concat(
                        "farmer__first_name", 
                        Value(" "), 
                        Left("farmer__last_name", 1),
                        Value(".")
                    ),
                ),
                default=Value("Anonymous"),
                output_field=CharField(),
            ),
            "transaction_quantity": Subquery(
                out_going_quantity.values("quantity")[:1],
                output_field=CharField(),
            ),
            "image_url": Case(
                When(image="", then=Value("")),
                When(
                    type=sup_const.NODE_TYPE_FARM,
                    farmer__consent_status=sup_const.GRANTED,
                    then=Concat(Value(settings.MEDIA_URL), F("image"))
                ),
                output_field=CharField(),
                default=Value(""),
            ),
        }

    def _get_products(self, actor_id, transactions, source_transaction):
        """To perform function _get_products."""
        source_txn_product = source_transaction.product
        product_values = (
            "name",
            "theme_name",
            "description",
            "direction",
            "theme_description",
            "image_url",
        )
        lan = translation.get_language().split("-")[0]

        theme_product_subquery = ConsumerInterfaceProduct.objects.filter(
            theme=self.theme, product_id=OuterRef("pk")
        )

        products = Product.objects.order_by().annotate(
            theme_name=Subquery(
                theme_product_subquery.values(f"name_{lan}")[:1]
            ),
            theme_description=Subquery(
                theme_product_subquery.values(f"description_{lan}")[:1]
            ),
            theme_image=Subquery(theme_product_subquery.values("image")[:1]),
            image_url=Case(
                When(
                    theme_image=None,
                    then=Concat(Value(settings.MEDIA_URL), F("image")),
                ),
                output_field=CharField(),
                default=Concat(Value(settings.MEDIA_URL), F("theme_image")),
            ),
        )

        outgoing_products_filter = {
            (
                "batches__outgoing_transactions__"
                "externaltransaction__source_id"
            ): actor_id,
            "batches__outgoing_transactions__in": transactions,
        }

        incoming_products_filter = {
            (
                "batches__outgoing_transactions__"
                "externaltransaction__destination_id"
            ): actor_id,
            "batches__outgoing_transactions__in": transactions,
        }
        outgoing_products = products.filter(
            **outgoing_products_filter
        ).distinct("id")

        incoming_products = products.filter(
            **incoming_products_filter
        ).distinct("id")

        if source_transaction.is_external:
            show_internal_product = False
        else:
            show_internal_product = all(
                (
                    source_transaction.internaltransaction.node_id == actor_id,
                    source_txn_product not in incoming_products,
                    source_txn_product not in outgoing_products,
                )
            )

        common_products = incoming_products.filter(id__in=outgoing_products)

        outgoing_products = (
            outgoing_products.exclude(pk__in=common_products)
            .annotate(
                direction=Value(prod_const.OUTGOING, output_field=CharField())
            )
            .values(*product_values)
        )

        incoming_products = (
            incoming_products.exclude(pk__in=common_products)
            .annotate(
                direction=Value(prod_const.INCOMING, output_field=CharField()),
            )
            .values(*product_values)
        )

        common_products = common_products.annotate(
            direction=Value(
                prod_const.INCOMING_AND_PROCESSED, output_field=CharField()
            )
        ).values(*product_values)

        source_txn_products = (
            products.filter(pk=source_txn_product.id)
            .annotate(
                direction=Value(prod_const.PROCESSED, output_field=CharField())
            )
            .values(*product_values)
            if show_internal_product
            else []
        )

        return (
                list(source_txn_products)
                + list(common_products)
                + list(outgoing_products)
                + list(incoming_products)
        )

    @staticmethod
    def _get_image_id_map(actors: QuerySet):
        """To perform function _get_image_id_map."""
        return dict(
            map(
                lambda x: (x.id, x.image_url),
                actors.only("id", "image").distinct("id").iterator(),
            )
        )

    def _actor_data(
            self, actors, source_transaction, transactions, external_sources
    ):
        """To perform function _actor_data."""
        for actor in actors:
            theme_actor = ConsumerInterfaceActor.objects.filter(
                theme=self.theme, actor_id=actor["id"]
            ).last()

            # Assign theme_actor.image_url if it exists and is not empty
            # Otherwise, assign by popping "image_url" from actor dictionary
            actor["image"] = (
                theme_actor.image_url
                if theme_actor and theme_actor.image_url
                else actor.pop("image_url", None)
            )

            # Assign theme_actor.description if it exists and is not empty
            # Otherwise, assign by popping "description" from actor dictionary
            actor["description_basic"] = (
                theme_actor.description
                if theme_actor and theme_actor.description
                else actor.pop("description_basic", None)
            )

            # Assign theme_actor.name if it exists and is not empty
            # Otherwise, assign by popping "name" from actor dictionary
            actor["name"] = (
                theme_actor.name
                if theme_actor and theme_actor.name
                else actor.pop("name", None)
            )

            claims = AttachedCompanyClaim.objects.filter(
                node_id=actor["id"]
            ).annotate(name=F("claim__name")).values_list(
                "claim_id", "name")

            actor["claims"] = list(
                map(lambda c: {"id": library.encode(c[0]),
                               "name": c[1]}, claims))

            supply_chain_id = actor.pop("supply_chains")
            operation = Operation.objects.filter(
                primary_node_supplychain__node=actor["id"],
                primary_node_supplychain__supply_chain=supply_chain_id,
            ).first()
            actor["primary_operation"] = (
                operation.name if operation else "Actor"
            )
            if not actor["image"]:
                stage_theme = (
                    ConsumerInterfaceStage.objects.filter(
                        theme=self.theme,
                        operation__name__icontains=actor["primary_operation"],
                    )
                    .only("image")
                    .last()
                )
                theme_image = stage_theme.image if stage_theme else None
                if theme_image:
                    actor["image"] = theme_image.url
            if (
                    actor["type"] == NODE_TYPE_FARM
                    and not actor["description_basic"]
            ):
                if self.theme:
                    if self.theme.farmer_description:
                        template = Template(self.theme.farmer_description)
                        context = Context(actor)
                        actor["description_basic"] = template.render(context)

            actor["products"] = self._get_products(
                actor["id"], transactions, source_transaction
            )

            # source_transaction will be the tracking transaction
            if actor["id"] in [source_transaction.destination.id]:
                transaction_quantity = source_transaction._destination_quantity
                actor["transaction_quantity"] = transaction_quantity

            actor["external_sources"] = []
            if actor["id"] in external_sources:
                actor["external_sources"] = external_sources[actor["id"]]

            actor["id"] = library.encode(actor["id"])

    def _get_external_sources(self, transactions):
        """Retrieves the external sources associated with the given
        transactions.

        Args:
            transactions: A list or queryset of transactions.

        Returns:
            A dictionary mapping batch nodes to lists of their corresponding
            external sources.
        """
        internal_transactions = (
            self.instance.source_transaction.get_parent_transactions(
                only_internal=True
            )
        )
        source_batches = SourceBatch.objects.filter(
            Q(transaction__in=transactions)
            | Q(transaction__in=internal_transactions),
            batch__external_source__isnull=False,
            batch__node__isnull=False,
        )

        data_dict = defaultdict(list)
        [
            data_dict[node].append(source)
            for node, source in source_batches.values_list(
            "batch__node", "batch__external_source"
        )
        ]

        return data_dict


def get_mapped_wallets(wallets_ids: list) -> dict:
    """
    Get wallets with ids and convert it in to dictionary.
    Each value dict is mapped with its id for quick access.
    eg:
        {
            '1': {
                'id': 1,
                'account_id': 0.12344,
                ....}}
    """
    wallet_values = (
        "id",
        "account_id",
        "public",
        "wallet_type",
        "explorer_url",
    )
    wallets = (
        BlockchainWallet.objects.filter(pk__in=wallets_ids)
        .annotate(
            explorer_url=Case(
                When(
                    wallet_type=sup_const.BLOCKCHAIN_WALLET_TYPE_HEDERA,
                    then=Concat(
                        Value(
                            settings.HEDERA_ACCOUNT_EXPLORER.format(
                                account_id=""
                            )
                        ),
                        F("account_id"),
                    ),
                ),
                output_field=CharField(),
                default=Value(""),
            )
        )
        .values(*wallet_values)
    )
    return dict(map(lambda wallet: (wallet["id"], wallet), wallets))


def map_idencode(data):
    """To perform function map_idencode."""
    list(map(lambda x: x.update({"id": library._encode(x["id"])}), data))


def get_primary_operations(node_id) -> dict:
    """To get primary operation against a node."""
    node = (
        Node.objects.filter(pk=node_id)
        .only("id")
        .prefetch_related("supply_chains")
        .first()
    )
    operations = Operation.objects.filter(
        primary_node_supplychain__node=node.id,
        primary_node_supplychain__supply_chain=node.supply_chains.first(),
    ).values_list("name", flat=True)
    return operations[0]


class TraceTransactionsWithBatchActorSerializer(AbstractTraceSerializer):
    """Class to handle TraceTransactionsWithBatchActorSerializer and
    functions."""

    @property
    def data(self):
        """To perform function ata."""
        return self.get_transactions()
    
    @staticmethod
    def _get_source_name(transaction):
        """Return source name according to consent status"""
        if transaction.source.is_farm() and \
            transaction.source.farmer.consent_status != GRANTED:
            return "Anonymous"
        return transaction.source.full_name

    def get_transactions(self):
        """To perform function get_transactions."""
        actor = self._get_actor()
        filters = self._get_filters(actor)

        data = []
        transactions = self.parent_transactions().filter(
            transaction_type=txn_const.TRANSACTION_TYPE_EXTERNAL
        )
        source_transaction = self.instance.source_transaction
        actor_transactions = self.get_actor_wise_transaction_list(
            transactions, source_transaction
        )

        transactions = Transaction.objects.filter(
            pk__in=actor_transactions[actor.id], **filters
        )
        total_count = transactions.count()

        # Getting all wallet ids from the transactions.
        wallets_ids = list(
            itertools.chain(
                *transactions.values_list(
                    "externaltransaction__destination_wallet_id",
                    "externaltransaction__source_wallet_id",
                )
            )
        )

        if source_transaction.is_internal:
            wallets_ids += [
                source_transaction.internaltransaction.node_wallet_id,
            ]

        mapped_wallets = get_mapped_wallets(wallets_ids)
        limit, offset = self._get_pagination_index()
        transactions = transactions[offset: (limit + offset)]  # noqa: E203
        for transaction in transactions.iterator():
            product = transaction.product.consumerinterfaceproduct_set.filter(
                theme=self.theme
            ).last()
            item = {
                "date": transaction.date.timestamp(),
                "verification_method": transaction.verification_method,
                "product_name": (
                    product.name if product else transaction.product.name
                ),
                "source_name": self._get_source_name(transaction),
                "source_id": transaction.source.idencode,
                "destination_name": transaction.destination.full_name,
                "destination_id": transaction.destination.idencode,
                "quantity": transaction.destination_quantity,
                "verification": transaction.verification,
                "source_wallet": mapped_wallets[transaction.source_wallet.id],
                "destination_wallet": mapped_wallets[
                    transaction.destination_wallet.id
                ],
                "blockchain_address": transaction.blockchain_address,
                "explorer_url": transaction.explorer_url,
                "wallet_type": transaction.wallet_type,
            }
            if transaction.is_external:
                if transaction.source == actor:
                    item["tittle"] = (
                            OUTGOING_DESCRIPTION % item["destination_name"]
                    )
                else:
                    item["tittle"] = INCOMING_DESCRIPTION % item["source_name"]
            else:
                item["tittle"] = PROCESSED_DESCRIPTION % item["source_name"]
            data.append(item)
        return {"count": total_count, "transactions": data}

    def _get_actor(self):
        """To perform function _get_actor."""
        try:
            actor = self.args[0]
        except IndexError:
            raise BadRequest("get_transaction() arguments required.")
        if actor.__class__.__name__ != "Node":
            raise BadRequest("Not an actor object.")
        return actor

    def _get_pagination_index(self):
        try:
            limit, offset = self.args[1]
        except KeyError:
            limit, offset = 20, 0
        return int(limit), int(offset)

    def _get_filters(self, actor):
        try:
            filters = self.args[2]
        except KeyError:
            filters = {}

        # adding extra filters for actor perspective direction.
        if "type" in filters:
            _type = filters.pop("type").lower()
            if _type == INCOMING.lower():
                filters["externaltransaction__destination"] = actor
            if _type == OUTGOING.lower():
                filters["externaltransaction__source"] = actor
            if _type == PROCESSED.lower():
                filters["internaltransaction__node"] = actor
        if "search" in filters:
            search = filters.pop("search").lower()
            filters[
                "externaltransaction__destination__name__icontains"
            ] = search
        return filters

    def get_actor_wise_transaction_list(
            self, transactions, source_transaction
    ):
        """Returns a grouped transactions against each actor."""

        # create key with language
        lan = translation.get_language()
        key = (
            f"{self.instance.source_transaction.id}"
            f"_actor_transactions"
            f"_{lan}"
        )

        # get data from cache is any.
        cached_data = filesystem_cache.get(key)
        if cached_data is not None:
            return cached_data

        # build data since cache is not available.
        data = defaultdict(list)
        for transaction in transactions:
            data[transaction.externaltransaction.source_id].append(
                transaction.id
            )
            data[transaction.externaltransaction.destination_id].append(
                transaction.id
            )
        if source_transaction.is_internal:
            data[source_transaction.source.id].append(source_transaction.id)

        # cache built data.
        filesystem_cache.set(key, data)

        return data
