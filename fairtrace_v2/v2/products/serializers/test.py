import itertools

from common import library
from django.conf import settings
from django.db.models import Case
from django.db.models import CharField
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Sum
from django.db.models import Value
from django.db.models import When
from v2.claims import constants as claim_const
from v2.claims.models import AttachedBatchClaim
from v2.supply_chains import constants as sup_const
from v2.supply_chains.models import BlockchainWallet
from v2.supply_chains.models import Node
from v2.supply_chains.models import Operation
from v2.transactions import constants as txn_const
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import InternalTransaction
from v2.transactions.models import Transaction


def map_idencode(data):
    """To perform function map_idencode."""
    list(map(lambda x: x.update({"id": library._encode(x["id"])}), data))


def get_primary_operations(node: Node) -> dict:
    """Get primary operation."""
    operations = Operation.objects.filter(
        primary_node_supplychain__node=node,
        primary_node_supplychain__supply_chain=node.supply_chains.first(),
    ).values("id", "name")
    map_idencode([operations[0]])
    return operations[0]


def get_connected_to(transactions, node) -> dict:
    """Get connected to node map."""
    connected_to_ids = transactions.annotate(
        actor_id=Case(
            When(
                Q(
                    transaction_type=txn_const.TRANSACTION_TYPE_EXTERNAL,
                    externaltransaction__source=node,
                ),
                then="externaltransaction__destination_id",
            ),
            When(
                Q(
                    transaction_type=txn_const.TRANSACTION_TYPE_EXTERNAL,
                    externaltransaction__destination=node,
                ),
                then="externaltransaction__source_id",
            ),
            When(
                transaction_type=txn_const.TRANSACTION_TYPE_INTERNAL,
                then="internaltransaction__node_id",
            ),
            output_field=IntegerField(),
            default=Value("0"),
        )
    ).values_list("actor_id", flat=True)

    connected_to = Node.objects.filter(pk__in=connected_to_ids).values(
        "id", "latitude", "longitude"
    )
    map_idencode(connected_to)
    return connected_to


def get_mapped_wallets(wallets_ids):
    """To perform function get_mapped_wallets."""
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
                    then=Value(
                        settings.HEDERA_ACCOUNT_EXPLORER.format(
                            account_id=F("account_id")
                        )
                    ),
                ),
                output_field=CharField(),
                default=Value(""),
            )
        )
        .values(*wallet_values)
    )
    return dict(map(lambda wallet: (wallet["id"], wallet), wallets))


def clean_transaction_data(transaction, mapped_wallets):
    """To perform function clean_transaction_data."""
    empty_wallet_data = {
        "id": "",
        "account_id": "",
        "public": "",
        "wallet_type": "",
        "explorer_url": "",
    }

    transaction["logged_time"] = transaction["logged_time"].timestamp()
    transaction["source_quantity"] = transaction.pop("_source_quantity", None)
    transaction["destination_quantity"] = transaction.pop(
        "_destination_quantity", None
    )

    if "source_wallet" in transaction:
        source_wallet = mapped_wallets[transaction["source_wallet"]]
        transaction["source_wallet"] = source_wallet
    else:
        transaction["source_wallet"] = empty_wallet_data

    if "destination_wallet" in transaction:
        destination_wallet = mapped_wallets[transaction["destination_wallet"]]
        transaction["destination_wallet"] = destination_wallet
    else:
        transaction["destination_wallet"] = empty_wallet_data

    if "source" in transaction:
        transaction["source_id"] = library._encode(transaction.get("source"))
    else:
        transaction["source_id"] = transaction.source.idencode
    if "destination" in transaction:
        transaction["destination_id"] = library._encode(
            transaction.get("destination")
        )
    else:
        transaction["destination_id"] = transaction.destination.idencode


def get_transactions(transactions, node: Node) -> QuerySet:
    """Filter out actor specific transactions."""
    return transactions.filter(
        Q(
            Q(externaltransaction__source=node)
            | Q(externaltransaction__destination=node)
        )
        | Q(
            Q(internaltransaction__node=node)
            & Q(internaltransaction__mode=txn_const.TRANSACTION_MODE_MANUAL)
        )
    )


class TraceOperational:
    """Class to handle TraceOperational and functions."""

    transaction_id_map = {}

    actor_ids_values = (
        "externaltransaction__source_id",
        "externaltransaction__destination_id",
        "internaltransaction__node_id",
    )
    actor_list_values = (
        "id",
        "blockchain_address",
        "type",
        "status",
        "latitude",
        "longitude",
        "country",
        "province",
        "description_basic",
        "image",
        "date_joined",
    )

    def to_representation(self, instance):
        """To perform function to_representation."""
        (
            parent_transactions,
            internal_transactions,
            external_transactions,
        ) = self.get_transactions(instance)

        return self.collect_actor_data(
            instance,
            parent_transactions,
            internal_transactions,
            external_transactions,
        )

    def collect_actor_data(
        self,
        instance,
        parent_transactions,
        internal_transactions,
        external_transactions,
    ):
        """Get parent transaction actors."""

        # Get the actors involved in the parent transactions
        actors_ids = itertools.chain(
            *parent_transactions.values_list(*self.actor_ids_values)
        )
        # duplicate objects will be returned. distinct() is an expensive query.
        actors = Node.objects.filter(pk__in=set(actors_ids))

        # create a list of actor data
        actor_list = actors.values(*self.actor_list_values)

        # map helps to avoid get calls on queryset and will help to optimize
        # it with only used fields later on.
        actors_id_map = dict(map(lambda x: (x.id, x), actors))

        self.update_transaction_id_map(
            internal_transactions, external_transactions
        )

        actor_list = self.update_actor_list(
            actor_list, actors_id_map, parent_transactions
        )

        return actor_list

    @staticmethod
    def get_transactions(instance):
        """To perform function get_transactions."""
        # Getting parent transaction objects and ids
        transactions = instance.source_transaction.get_parent_transactions()
        parent_transactions = transactions
        parent_transactions_ids = parent_transactions.values_list(
            "id", flat=True
        )

        # Get separated transaction sets internal and external
        internal_transactions = InternalTransaction.objects.filter(
            pk__in=parent_transactions_ids
        )
        external_transactions = ExternalTransaction.objects.filter(
            pk__in=parent_transactions_ids
        )

        return (
            parent_transactions,
            internal_transactions,
            external_transactions,
        )

    def update_actor_list(
        self, actor_list, actors_id_map, parent_transactions
    ):
        """To update actor list."""
        data = []
        for actor in actor_list:
            actor_obj = actors_id_map[actor["id"]]
            actor["name"] = actor_obj.full_name
            actor["short_name"] = actor_obj.short_name
            actor["date_joined"] = (
                actor["date_joined"].timestamp()
                if actor["date_joined"]
                else None
            )
            actor["managers"] = list(
                map(
                    library._encode,
                    actor_obj.managers.values_list("id", flat=True),
                )
            )
            actor["primary_operation"] = get_primary_operations(actor_obj)
            transactions = get_transactions(parent_transactions, actor_obj)
            actor["transaction_count"] = transactions.count()
            actor["transaction_quantity"] = transactions.aggregate(
                s_qty=Sum("_source_quantity")
            )["s_qty"]
            actor["connected_to"] = get_connected_to(
                parent_transactions, actor_obj
            )
            actor["transactions"] = list(
                map(
                    lambda txn_id: self.transaction_id_map[txn_id],
                    transactions.values_list("id", flat=True),
                )
            )
            data.append(actor)
        return data

    def update_transaction_id_map(
        self, internal_transactions, external_transactions
    ):
        """Updates the transaction id map."""
        external_txn_data = external_transactions.annotate(
            logged_time=F("created_on"),
        ).values(
            "id",
            "date",
            "transaction_type",
            "logged_time",
            "_source_quantity",
            "_destination_quantity",
            "source",
            "source_wallet",
            "destination",
            "destination_wallet",
            "blockchain_address",
            "info_message_address",
        )
        internal_txn_data = internal_transactions.annotate(
            logged_time=F("created_on"),
            source=F("node_id"),
            destination=F("node_id"),
        ).values(
            "id",
            "date",
            "transaction_type",
            "logged_time",
            "_source_quantity",
            "_destination_quantity",
            "source",
            "destination",
            "blockchain_address",
            "info_message_address",
        )

        wallets_ids = list(
            itertools.chain(
                *external_transactions.values_list(
                    "destination_wallet_id", "source_wallet_id"
                )
            )
        )
        mapped_wallets = get_mapped_wallets(wallets_ids)

        transaction_data = sorted(
            list(internal_txn_data) + list(external_txn_data),
            key=lambda txn: txn["date"],
        )

        for transaction in transaction_data:
            clean_transaction_data(transaction, mapped_wallets)
            self.transaction_id_map[transaction["id"]] = transaction

    def get_stage_data(self, batch, actor_list, parent_transactions):
        """To perform function get_stage_data."""
        stage_actors_dict = batch.get_parent_actors_levels()
        for stage in sorted(stage_actors_dict.keys(), reverse=True):
            queryset = stage_actors_dict[stage]
            [library.encode(i["id"]) for i in queryset.values("id")]


def get_claims(instance):
    """To perform function get_claims."""
    attached_claim_ids = list(
        instance.claims.filter(
            attached_from=claim_const.ATTACHED_DIRECTLY,
            status=claim_const.STATUS_APPROVED,
        ).values_list("claim_id", flat=True)
    )
    # pair up clime and transactions
    attached_claim_ids = list(
        map(lambda _claim: (*_claim, None), attached_claim_ids)
    )

    transactions = instance.source_transaction.get_parent_transactions()
    transaction_ids = transactions.values_list("id", flat=True)

    transaction_claims = (
        AttachedBatchClaim.objects.filter(
            batch__source_transaction__in=transaction_ids,
            attached_from__in=[
                claim_const.ATTACHED_FROM_TRANSACTION,
                claim_const.ATTACHED_BY_INHERITANCE,
            ],
        )
        .annotate(transactions_id=F("batch__source_transaction_id"))
        .values_list("claim_id", "transactions_id")
    )

    claim_transactions = dict((*attached_claim_ids, *transaction_claims))
    claim_data = get_claims_data(claim_transactions.keys())
    transaction_data = get_claim_transaction_data(claim_transactions.values())
    processed_claim = []
    data = []
    for claim in claim_data.iterator():
        if claim["claim_id"] not in processed_claim:
            claim["transaction_data"] = transaction_data[
                claim_transactions[claim["claim_id"]]
            ]
            processed_claim.append(claim["claim_id"])
            data.append(claim)

    return data


def get_claims_data(claim_ids):
    """To perform function get_claims_data."""
    claim_annotations = {
        "name": F("claim__name"),
        "description_basic": F("claim__description_basic"),
        "description_full": F("claim__description_full"),
    }
    claim_values = (
        "claim_id",
        "name",
        "description_basic",
        "description_full",
        "attached_from",
        "status",
        "blockchain_address",
    )

    return (
        AttachedBatchClaim.objects.filter(claim_id__in=claim_ids)
        .annotate(**claim_annotations)
        .values(*claim_values)
    )


def get_claim_transaction_data(parent_transaction_ids):
    """To perform function get_claim_transaction_data."""
    data = {}
    transactions = Transaction.objects.filter(pk__in=parent_transaction_ids)

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
        }
        data[transaction.id] = item
    return data
