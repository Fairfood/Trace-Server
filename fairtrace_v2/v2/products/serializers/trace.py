"""Serializers for tracking related APIs."""
import copy
import datetime

from common import library as comm_lib
from common.exceptions import BadRequest
from django.template import Context
from django.template import Template
from rest_framework import serializers
from v2.claims import constants as claims_contants
from v2.claims.serializers import consumer_interface as claims_serializers
from v2.dashboard.models import CITheme
from v2.dashboard.models import ProgramStat
from v2.products.constants import INCOMING
from v2.products.constants import INCOMING_DESCRIPTION
from v2.products.constants import OUTGOING
from v2.products.constants import OUTGOING_DESCRIPTION
from v2.products.constants import PROCESSED
from v2.products.constants import PROCESSED_DESCRIPTION
from v2.products.models import Batch
from v2.products.serializers import consumer_interface as ci_prod_serializers
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Operation
from v2.supply_chains.serializers import functions as node_serializers
from v2.transactions import constants as trans_constants
from v2.transactions.serializers import consumer_interface as trans_serializers


class TraceBatchSerializer(serializers.ModelSerializer):
    """Serializer for trace a batch to show in the consumer interface.

    First the source transaction of the batch is taken and is then traced to
    the source transaction from the farmers. The actors in this chain is
    then separated into different stages in the order of their involvement
    in the supply chain. A general info is computed to be shown along with
    the details of the company. Claim data are shown at different staged
    including with the transaction, at each stage and a global list of
    claims is also shown.

    If a theme is passed as filter when tracing the batch, the theme is
    applied to the response data. But he theme has to be public, or owned by
    the company that owns the batch, or the owner should be connected to the
    owner of the theme in that supply chain.


    Known issues due to edge cases:
        - If an actor is part of a transaction chain at multiple positions, the
        consumer interface might be messed up. The actor along with all the
        corresponding transactions will only be shown at one stage.
        - The current method of tracing through the transactions can cause some
        issues in complex chains with multiple output products. This issue is
        noted and can be fixed by changing it to trace through batches. This
        change is postponed for later.
    """

    theme = None

    class Meta:
        model = Batch
        fields = ("id",)

    def combine_source_destination_products(
        self, source_products, destination_products
    ):
        """Products are received as separate list of source and destination
        products from the transaction details serializer, this needs to be
        combined to show in the products tab."""
        products_dict = {}
        all_products = source_products + destination_products
        for prod in all_products:
            if prod["id"] in products_dict:
                products_dict[prod["id"]]["type"].append(prod["type"])
                products_dict[prod["id"]]["incoming"] |= prod["incoming"]
                products_dict[prod["id"]]["outgoing"] |= prod["outgoing"]
                products_dict[prod["id"]]["processed"] |= prod["processed"]
            else:
                products_dict[prod["id"]] = copy.deepcopy(prod)
                products_dict[prod["id"]]["type"] = [prod["type"]]

        products = list(products_dict.values())

        for prod in products:
            prod["type"] = comm_lib._list_to_sentence(
                sorted(list(set(prod["type"])))
            ).capitalize()

        return products

        # for prod in source_products:
        #     products[prod['id']] = prod
        # for prod in destination_products:
        #     if prod['id'] in products:
        #         products[prod['id']]['type'] += ' & %s' % prod['type']
        #     else:
        #         prod['type'] = '%s' % prod['type']
        #         products[prod['id']] = prod
        # return list(products.values())

    def get_parent_actors(self, parent_transactions):
        """Method to categorize parent transactions into parent actors.

        To show all the list of all parent actors involved in the supply chain
        of the particular batch.
        It is computed from the parent transactions.

        Args:
            parent_transactions: transactions queryset
        """
        actors_dict = {}
        product_data = {}
        for transaction in parent_transactions:
            # comm_lib._time_since(intend=1, stage="Product data")
            source_products = []
            for prod in transaction.get_absolute_source_products():
                if prod.id in product_data:
                    prod_data = copy.deepcopy(product_data[prod.id])
                else:
                    prod_data = ci_prod_serializers.serialize_product(
                        prod, theme=self.theme
                    )
                    product_data[prod.id] = prod_data
                prod_data["outgoing"] = True
                prod_data["type"] = OUTGOING
                source_products.append(copy.deepcopy(prod_data))

            destination_products = []
            for prod in transaction.destination_products:
                if prod.id in product_data:
                    prod_data = copy.deepcopy(product_data[prod.id])
                else:
                    prod_data = ci_prod_serializers.serialize_product(
                        prod, theme=self.theme
                    )
                    product_data[prod.id] = prod_data
                prod_data["incoming"] = True
                prod_data["type"] = INCOMING
                destination_products.append(prod_data)

            # comm_lib._time_since(intend=1, stage="1st If")

            transaction_data = trans_serializers.serialize_transaction(
                transaction.transaction_object
            )
            incoming_transaction_data = dict(transaction_data)
            outgoing_transaction_data = dict(transaction_data)
            if (
                transaction_data["transaction_type"]
                == trans_constants.TRANSACTION_TYPE_EXTERNAL
            ):
                incoming_transaction_data["title"] = (
                    INCOMING_DESCRIPTION % transaction_data["source"]["name"]
                )
                incoming_transaction_data[
                    "direction"
                ] = trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
                outgoing_transaction_data["title"] = (
                    OUTGOING_DESCRIPTION
                    % transaction_data["destination"]["name"]
                )
                outgoing_transaction_data[
                    "direction"
                ] = trans_constants.EXTERNAL_TRANS_TYPE_OUTGOING
            else:
                incoming_transaction_data["title"] = (
                    PROCESSED_DESCRIPTION % transaction_data["source"]["name"]
                )
                incoming_transaction_data["direction"] = 0
                outgoing_transaction_data["title"] = (
                    PROCESSED_DESCRIPTION % transaction_data["source"]["name"]
                )
                outgoing_transaction_data["direction"] = 0
                for product in source_products:
                    product["type"] = PROCESSED
                    product["processed"] = True
                    product["incoming"] = False
                    product["outgoing"] = False
                for product in destination_products:
                    product["type"] = PROCESSED
                    product["processed"] = True
                    product["incoming"] = False
                    product["outgoing"] = False

            source_id = transaction_data["source"]["id"]
            destination_id = transaction_data["destination"]["id"]
            # comm_lib._time_since(intend=1, stage="2nd If")
            if transaction.is_external:
                if source_id in actors_dict:
                    actors_dict[source_id]["transaction_count"] += 1
                    actors_dict[source_id][
                        "transaction_quantity"
                    ] += transaction.source_quantity
                    actors_dict[source_id]["transactions"].append(
                        outgoing_transaction_data
                    )
                    actors_dict[source_id][
                        "source_products"
                    ] += source_products
                    actors_dict[source_id]["connected_to"].append(
                        transaction_data["destination"]["latlong"]
                    )
                else:
                    source = node_serializers.serialize_node_basic(
                        transaction.transaction_object.source
                    )
                    trn_source = transaction.transaction_object.source
                    _primary_operation = trn_source.get_primary_operation(self)
                    source["primary_operation"] = _primary_operation
                    source["transaction_count"] = 1
                    source[
                        "transaction_quantity"
                    ] = transaction.source_quantity
                    source["source_products"] = source_products
                    source["destination_products"] = []
                    source["transactions"] = [outgoing_transaction_data]
                    source["connected_to"] = [
                        transaction_data["destination"]["latlong"]
                    ]
                    actors_dict[source_id] = source

            # comm_lib._time_since(intend=1, stage="3rd If")

            if destination_id in actors_dict:
                actors_dict[destination_id]["transaction_count"] += 1
                actors_dict[destination_id]["transactions"].append(
                    incoming_transaction_data
                )
                actors_dict[destination_id][
                    "destination_products"
                ] += destination_products
                actors_dict[destination_id]["connected_to"].append(
                    transaction_data["source"]["latlong"]
                )
                if transaction.is_internal:
                    actors_dict[destination_id][
                        "transaction_quantity"
                    ] += transaction.destination_quantity

            else:
                destination = node_serializers.serialize_node_basic(
                    transaction.transaction_object.destination
                )
                trn_dest = transaction.transaction_object.destination
                _primary_operation = trn_dest.get_primary_operation(self)
                destination["primary_operation"] = _primary_operation
                destination["transaction_count"] = 1
                destination["destination_products"] = destination_products
                destination["source_products"] = []
                destination["transactions"] = [incoming_transaction_data]
                destination["connected_to"] = [
                    transaction_data["source"]["latlong"]
                ]
                destination[
                    "transaction_quantity"
                ] = transaction.destination_quantity
                actors_dict[destination_id] = destination
        #
        actors = actors_dict.values()

        for actor in actors:
            actor["products"] = self.combine_source_destination_products(
                actor.pop("source_products"), actor.pop("destination_products")
            )
            actor["connected_to"] = [
                dict(t)
                for t in {tuple(d.items()) for d in actor["connected_to"]}
            ]
            if (
                actor["type"] == NODE_TYPE_FARM
                and not actor["description_basic"]
            ):
                if self.theme:
                    if self.theme.farmer_description:
                        template = Template(self.theme.farmer_description)
                        context = Context(actor)
                        actor["description_basic"] = template.render(context)

            # actor['connected_to'] = list(set(actor['connected_to']))
            # actor['products'] = self.combine_source_destination_products(
            #     actor['source_products'], actor['destination_products'])
        return actors

    def get_stage_products(self, stage_actors):
        """Combining the products in the stage from multiple actors and
        multiple transactions."""
        products = []
        prod_ids = []
        for actor in stage_actors:
            for prod in actor["products"]:
                if prod["id"] not in prod_ids:
                    prod_ids.append(prod["id"])
                    prod_data = copy.deepcopy(prod)
                    prod_data.pop("type")
                    products.append(prod_data)
        return products

    def annotate_claim_data(self, stages, batch_claims):
        """Data of each claims needs to be annotated to the transaction, stage,
        and a global list."""
        data = []
        global_claims = {}
        claim_ids = []
        for stage in stages:
            for actor in stage["actors"]:
                actor_claims = {}
                actor_claims_ids = []
                for transaction in actor["transactions"]:
                    for claim in (
                        transaction["claims"] if transaction["claims"] else []
                    ):
                        if claim["status"] == claims_contants.STATUS_APPROVED:
                            txt_att = claims_contants.ATTACHED_FROM_TRANSACTION
                            new = (
                                True
                                if claim["attached_from"] == txt_att
                                else False
                            )
                            if (
                                claim["claim_id"] not in actor_claims_ids
                                or new
                            ):
                                actor_claims[claim["claim_id"]] = claim
                                actor_claims_ids.append(claim["claim_id"])
                            claim_copy = copy.deepcopy(claim)
                            if (
                                self.theme
                                and self.theme.default_claim_id
                                == claim_copy["claim_id"]
                            ):
                                claim_copy["primary_claim"] = True
                            claim_copy["transaction_data"] = {
                                "date": transaction["date"],
                                "blockchain_address": transaction[
                                    "blockchain_address"
                                ],
                                "wallet_type": transaction["wallet_type"],
                                "explorer_url": transaction["explorer_url"],
                                "info_message_address": transaction[
                                    "info_message_address"
                                ],
                                "info_explorer_url": transaction[
                                    "info_explorer_url"
                                ],
                                "source": transaction["source"],
                                "source_wallet": transaction["source_wallet"],
                                "destination": transaction["destination"],
                                "destination_wallet": transaction[
                                    "destination_wallet"
                                ],
                                "quantity": transaction[
                                    "destination_quantity"
                                ],
                                "product": transaction["product"],
                                "logged_time": transaction["logged_time"],
                            }
                            if claim["claim_id"] not in claim_ids or new:
                                global_claims[claim["claim_id"]] = claim_copy
                                claim_ids.append(claim["claim_id"])
                            else:
                                for new_evidence in claim["evidences"]:
                                    for evidence in global_claims[
                                        claim["claim_id"]
                                    ]["evidences"]:
                                        if (
                                            evidence["added_by"]["id"]
                                            == new_evidence["added_by"]["id"]
                                        ):
                                            new = (
                                                evidence["data"]
                                                + new_evidence["data"]
                                            )
                                            evidence["data"] = [
                                                dict(t)
                                                for t in {
                                                    tuple(d.items())
                                                    for d in new
                                                }
                                            ]
                                            break
                                    else:
                                        global_claims[claim["claim_id"]][
                                            "evidences"
                                        ].append(new_evidence)

                actor["claims"] = list(actor_claims.values())

            if stage["actors"]:
                stage_data = {
                    "title": stage["title"],
                    "actor_name": stage["actor_name"],
                    "image": stage["image"],
                    "description": "",
                    "stage_products": self.get_stage_products(stage["actors"]),
                    "actors": stage["actors"],
                    "date": stage["date"],
                }
                data.append(stage_data)
        for claim in batch_claims:
            global_claims[claim["claim_id"]] = claim
            claim_ids.append(claim["claim_id"])
        claims = list(global_claims.values())
        return data, claims

    def get_stage_data(self, batch):
        """Data of each stage in the supply chain is split up using the
        primary_operation of the actor."""
        stages = []
        if not batch.source_transaction:
            actors = []
        else:
            parent_transactions = (
                batch.source_transaction.get_parent_transactions()
            )
            actors = self.get_parent_actors(parent_transactions)
        stage_actors_dict = batch.get_parent_actors_levels()
        for stage in sorted(stage_actors_dict.keys(), reverse=True):
            stage_actors_query_set = stage_actors_dict[stage]
            stage_actors_ids = [
                comm_lib._encode(i["id"])
                for i in stage_actors_query_set.values("id")
            ]
            stage_actors = []
            date = datetime.datetime(year=1999, month=12, day=31)
            for actor in actors:
                if actor["id"] in stage_actors_ids:
                    stage_actors.append(actor)
                for tr in actor["transactions"]:
                    if (
                        tr["direction"]
                        == trans_constants.EXTERNAL_TRANS_TYPE_OUTGOING
                    ):
                        date = max(
                            [
                                date,
                                datetime.datetime.utcfromtimestamp(tr["date"]),
                            ]
                        )
            stage_actors = sorted(
                stage_actors, key=lambda k: str(k["image"]), reverse=True
            )
            if stage_actors:
                operations = list(
                    set([i["primary_operation"]["name"] for i in stage_actors])
                )
                title = comm_lib._list_to_sentence(operations)
                image = None
                op_id = comm_lib._decode(
                    stage_actors[0]["primary_operation"]["id"]
                )
                if self.theme and self.theme.stages.filter(
                    operation__id=op_id
                ):
                    stage = self.theme.stages.filter(
                        operation__id=op_id
                    ).first()
                    actor_name = stage.actor_name
                    image = stage.image_url
                    title = stage.title
                elif len(stage_actors) == 1:
                    actor_name = stage_actors[0]["name"]
                    operation = Operation.objects.get(
                        id=comm_lib._decode(
                            stage_actors[0]["primary_operation"]["id"]
                        )
                    )
                    if operation.image:
                        image = operation.image.url
                else:
                    actor_name = "%d %ss" % (
                        len(stage_actors),
                        stage_actors[0]["primary_operation"]["name"],
                    )
                stages.append(
                    {
                        "actors": stage_actors,
                        "actor_name": actor_name,
                        "title": title,
                        "date": date.strftime("%d %B %Y"),
                        "image": image,
                    }
                )
        return stages

    def get_interface_data(self, batch):
        """The function to get the complete data is moved to a separate
        function to keep the to_representation() method clean."""
        batch_claims = batch.claims.filter(
            attached_from=claims_contants.ATTACHED_DIRECTLY,
            status=claims_contants.STATUS_APPROVED,
        )
        batch_claims_data = []
        owner_data = node_serializers.serialize_node_basic(batch.node)
        prod_data = ci_prod_serializers.serialize_product(
            batch.product, theme=self.theme
        )
        wallet_data = {
            "id": "",
            "account_id": "",
            "public": "",
            "wallet_type": "",
            "explorer_url": "",
        }
        source_wallet = wallet_data.copy()
        if batch.source_wallet:
            source_wallet["id"] = batch.source_wallet.id
            source_wallet["account_id"] = batch.source_wallet.account_id
            source_wallet["public"] = batch.source_wallet.public
            source_wallet["wallet_type"] = batch.source_wallet.wallet_type
            source_wallet["explorer_url"] = batch.source_wallet.explorer_url

        destination_wallet = wallet_data.copy()
        if batch.destination_wallet:
            destination_wallet["id"] = batch.destination_wallet.id
            destination_wallet[
                "account_id"
            ] = batch.destination_wallet.account_id
            destination_wallet["public"] = batch.destination_wallet.public
            destination_wallet[
                "wallet_type"
            ] = batch.destination_wallet.wallet_type
            destination_wallet[
                "explorer_url"
            ] = batch.destination_wallet.explorer_url

        for batch_claim in batch_claims:
            claim_data = claims_serializers.serialize_batch_claim(batch_claim)
            if self.theme and self.theme.default_claim == batch_claim.claim:
                claim_data["primary_claim"] = True
            claim_data["transaction_data"] = {
                "blockchain_address": batch_claim.blockchain_address,
                "date": batch_claim.created_on.timestamp(),
                "destination": owner_data,
                "source": owner_data,
                "quantity": batch.initial_quantity,
                "product": prod_data,
                "logged_time": int(batch_claim.created_on.timestamp()),
                "source_wallet": source_wallet,
                "wallet_type": "",
                "explorer_url": "",
                "info_message_address": batch.info_message_address,
                "info_explorer_url": "",
                "destination_wallet": destination_wallet,
            }
            if batch.node_wallet:
                claim_data["transaction_data"].update(
                    {
                        "wallet_type": batch.node_wallet.wallet_type,
                        "explorer_url": batch.node_wallet.explorer_url,
                    }
                )
            batch_claims_data.append(claim_data)
        product_details = ci_prod_serializers.serialize_product(
            batch.product, theme=self.theme
        )

        stages = self.get_stage_data(batch)
        stage_data, global_claims = self.annotate_claim_data(
            stages, batch_claims_data
        )

        program_details = {}
        if self.theme and self.theme.program:
            program_details["id"] = self.theme.program.idencode
            program_details["tittle"] = self.theme.program.title
            program_details["description"] = self.theme.program.description
            stats = ProgramStat.objects.filter(program=self.theme.program.id)
            program_details["program_stats_details"] = stats.values(
                "name", "value", "is_visible", "symbol"
            )

        interface_data = {
            "stages": stage_data,
            "claims": global_claims,
            "product": product_details,
            "program": program_details if product_details else None,
        }
        return interface_data

    def to_representation(self, batch):
        """To perform function to_representation."""
        # comm_lib._time_since(intend=0, stage="Start Tracing batch")

        theme = None
        theme_name = self.context["request"].query_params.get("theme", None)
        if theme_name:
            try:
                theme = CITheme.objects.get(name=theme_name)
            except CITheme.DoesNotExist:
                raise BadRequest("Invalid theme")
            if not theme.is_public:
                batch_chain = batch.node.get_chain(
                    supply_chain=batch.product.supply_chain, include_self=True
                )
                if theme.node not in batch_chain:
                    raise BadRequest("Batch cannot be traced with this theme")
        self.theme = theme
        if theme:
            self.theme.check_language_rollback()
        data = self.get_interface_data(batch)
        return data
