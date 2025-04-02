from v2.supply_chains.models.profile import Farmer
import pandas as pd
from pprint import pprint

from v2.projects.models import Payment
from v2.supply_chains.models.profile import BlockchainWallet, Farmer
from v2.transactions.models import ExternalTransaction, InternalTransaction
from v2.products.models import Batch
from v2.supply_chains.constants import BLOCKCHAIN_WALLET_TYPE_HEDERA
# FarmerModel = models.get_model("supply_chains", "Farmer")

def get_duplicate_farmers():
    farmers = Farmer.objects.values(
        'pk',
        'first_name', 
        'last_name', 
        'city', 
        'province', 
        'country',
        'identification_no')
    df = pd.DataFrame(list(farmers))
    selected_columns = ['first_name', 'last_name', 
                        'city', 'province', 'country',
                        'identification_no']
    duplicates = df[df.duplicated(subset=selected_columns, keep=False)]


# FarmerModel = models.get_model("supply_chains", "Farmer")

def get_duplicate_farmers(companies=None):
    if companies:
        farmers_ids = []
        for company in companies:
            farmers_ids.extend(list(
                company.get_suppliers().filter(type=2).values_list('pk', flat=True)))
        farmers = Farmer.objects.filter(pk__in=farmers_ids)
    else:
        farmers = Farmer.objects.all()

    farmers = farmers.values(
        'pk',
        'first_name', 
        'last_name', 
        'city', 
        'province', 
        'country',
        'identification_no')
    df = pd.DataFrame(list(farmers))
    selected_columns = ['first_name', 'last_name', 
                        'city', 'province', 'country',
                        'identification_no']
    duplicates = df[df.duplicated(subset=selected_columns, keep=False)]
    print(f"{len(duplicates)} farmer duplicated in total of {farmers.count()} farmers.")
    return duplicates.groupby(selected_columns)

def get_items_to_merge(farmer_ids):
    external_transactions = ExternalTransaction.objects.filter(
        source__in=farmer_ids)
    
    internal_transactions = InternalTransaction.objects.filter(
        node__in=farmer_ids)
    paymets = Payment.objects.filter(destination__in=farmer_ids)
    batches = Batch.objects.filter(node__in=farmer_ids)
    return (
        external_transactions, 
        internal_transactions, 
        paymets,
        batches)

def merge_items(main_farmer, items):
    external_transaction_update_list = []
    internal_transaction_update_list = []
    payment_update_list = []
    batch_update_list = []

    source_wallet = BlockchainWallet.objects.filter(
            wallet_type=BLOCKCHAIN_WALLET_TYPE_HEDERA, default=True
        ).last()

    for ext_transaction in items[0]:
        ext_transaction.source_id = main_farmer
        ext_transaction.source_wallet_id = source_wallet.pk if source_wallet else None
        external_transaction_update_list.append(ext_transaction)
    for int_transaction in items[1]:
        int_transaction.node_id = main_farmer
        internal_transaction_update_list.append(int_transaction)
    for payment in items[2]:
        payment.destination_id = main_farmer
        payment_update_list.append(payment)
    for batch in items[3]:
        batch.node_id = main_farmer
        batch.node_wallet_id = source_wallet.pk if source_wallet else None
        batch_update_list.append(batch)
    return (
        external_transaction_update_list,
        internal_transaction_update_list,
        payment_update_list,
        batch_update_list)

def process_merge(ext_objs, int_objs, pay_objs, bat_objs, farmers_to_delete):
    ExternalTransaction.objects.bulk_update(ext_objs, ['source_id', 'source_wallet_id'])
    InternalTransaction.objects.bulk_update(int_objs, ['node_id'])
    Payment.objects.bulk_update(pay_objs, ['destination_id'])
    Batch.objects.bulk_update(bat_objs, ['node_id', 'node_wallet_id'])
    items = get_items_to_merge(farmers_to_delete)
    avaliable_items = [item.exists() for item in items]
    print(avaliable_items)
    if any(avaliable_items):
        print('Error: Some items are not merged.')
    else:
        d = Farmer.objects.filter(pk__in=farmers_to_delete).delete()
        print(f"Removed {len(farmers_to_delete)} farmers.")
        pprint(d)

def remove_wrong_duplicates(main_farmer, duplicate_farmers):
    f = Farmer.objects.get(pk=main_farmer)
    buyer_id = f.get_buyers().last().id
    t = ExternalTransaction.objects.filter(source__in=duplicate_farmers)
    wrong_duplicates = t.exclude(destination_id=buyer_id)
    return list(set(duplicate_farmers) - set(wrong_duplicates.values_list(
        'source_id', flat=True)))


def remove_duplicates(companies=None):
    duplicates = get_duplicate_farmers(companies)
    farmers_to_delete = []
    external_transaction_merge_list = []
    internal_transaction_merge_list = []
    payment_merge_list = []
    batch_merge_list = []
    for _, group in duplicates:
        farmer_ids = group.pk.to_list()
        farmer_ids.sort()
        main_farmer, duplicate_farmers = farmer_ids[0], farmer_ids[1:] 
        duplicate_farmers = remove_wrong_duplicates(main_farmer, duplicate_farmers)
        items = get_items_to_merge(duplicate_farmers)
        avaliable_items = [item.exists() for item in items]
        if any(avaliable_items):
            mergable_items = merge_items(main_farmer, items)
            external_transaction_merge_list.extend(mergable_items[0])
            internal_transaction_merge_list.extend(mergable_items[1])
            payment_merge_list.extend(mergable_items[2])
            batch_merge_list.extend(mergable_items[3])
        farmers_to_delete.extend(duplicate_farmers)

    process_merge(
        external_transaction_merge_list,
        internal_transaction_merge_list,
        payment_merge_list,
        batch_merge_list, farmers_to_delete)

    print(f"Updated {len(external_transaction_merge_list)} external transactions.")
    print(f"Updated {len(internal_transaction_merge_list)} internal transactions.")
    print(f"Updated {len(batch_merge_list)} batches.")
    print('Done')