"""Serializers of transactions for consumer interface APIs.

DRF serializer is avoided to reduce page load time since, since huge
amount of data needs to be serialized.
"""
from common import library as common_lib
from django.core.cache import cache
from django.utils import translation
from v2.claims.serializers import consumer_interface as ci_claims_serializers
from v2.supply_chains.serializers import functions as ci_node_serializers
from v2.transactions.models import Transaction


def get_transaction_base_data(
    transaction=None, transaction_id=None, force_reload=False
):
    """Get transaction data."""
    if not transaction_id:
        try:
            transaction_id = transaction.id
        except Exception:
            raise AssertionError(
                "Either Transaction object or transaction_id is required"
            )
    key = "transaction_base_data_%s" % common_lib._encode(transaction_id)
    lang_key = "transaction_cached_lang_%s" % common_lib._encode(
        transaction_id
    )

    if not transaction:
        try:
            transaction = Transaction.objects.get(id=transaction_id)
        except Exception:
            raise AssertionError(
                "Either Transaction object or transaction_id is required"
            )

    if not force_reload:
        transaction_data = cache.get(key)
        transaction_lang = cache.get(lang_key)
        if transaction_data:
            # Claims are updated to avoid translation problems.
            if transaction_lang != translation.get_language():
                transaction_data["claims"] = [
                    ci_claims_serializers.serialize_batch_claim(claim)
                    for claim in transaction.get_claims()
                ]
                cache.set(lang_key, translation.get_language())
            return transaction_data

    data = {}
    data["date"] = int(transaction.date.timestamp())
    data["transaction_type"] = transaction.transaction_type
    data["logged_time"] = transaction.created_on.timestamp()
    data["source_quantity"] = transaction.source_quantity
    data["destination_quantity"] = transaction.destination_quantity
    data["product"] = {"name": transaction.product.name}
    data["claims"] = [
        ci_claims_serializers.serialize_batch_claim(claim)
        for claim in transaction.get_claims()
    ]
    data["source_id"] = transaction.source.id
    if transaction.source_wallet:
        data["source_wallet"] = {
            "id": transaction.source_wallet.id,
            "account_id": transaction.source_wallet.account_id,
            "public": transaction.source_wallet.public,
            "wallet_type": transaction.source_wallet.wallet_type,
            "explorer_url": transaction.source_wallet.explorer_url,
        }
    else:
        data["source_wallet"] = {
            "id": "",
            "account_id": "",
            "public": "",
            "wallet_type": "",
            "explorer_url": "",
        }
    data["destination_id"] = transaction.destination.id
    if transaction.destination_wallet:
        data["destination_wallet"] = {
            "id": transaction.destination_wallet.id,
            "account_id": transaction.destination_wallet.account_id,
            "public": transaction.destination_wallet.public,
            "wallet_type": transaction.destination_wallet.wallet_type,
            "explorer_url": transaction.destination_wallet.explorer_url,
        }
    else:
        data["destination_wallet"] = {
            "id": "",
            "account_id": "",
            "public": "",
            "wallet_type": "",
            "explorer_url": "",
        }

    data["wallet_type"] = transaction.wallet_type
    data["blockchain_address"] = transaction.blockchain_address
    data["explorer_url"] = transaction.explorer_url
    data["info_message_address"] = transaction.info_message_address
    data["info_explorer_url"] = transaction.info_explorer_url

    cache.set(key, data, None)
    cache.set(lang_key, translation.get_language())
    return data


def serialize_transaction(
    transaction=None, transaction_id=None, force_reload=False
):
    """Get transaction base data and append source and destination data onto
    it."""
    data = get_transaction_base_data(transaction, transaction_id, force_reload)
    products = []
    for batch in transaction.result_batches.all():
        products.append(batch.product.name)
        data["product"] = {"name": common_lib._list_to_sentence(products)}
    data["source"] = ci_node_serializers.serialize_node_blockchain(
        node_id=data["source_id"]
    )
    data["destination"] = ci_node_serializers.serialize_node_blockchain(
        node_id=data["destination_id"]
    )
    return data
