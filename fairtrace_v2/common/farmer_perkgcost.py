from django.db.models import Sum
from v2.products.models import Product
from v2.transactions.models import ExternalTransaction

NODE_TYPE_FARM = 2


def qs_sum(query_set, field):
    """To get queryset sum."""
    total = query_set.aggregate(Sum(field))[f"{field}__sum"]
    if not total:
        return 0
    return total


def get_unique_dict_list(dict_list):
    """To perform function get_unique_dict_list."""
    unq = [dict(t) for t in {tuple(d.items()) for d in dict_list}]
    return unq


txns = ExternalTransaction.objects.filter(
    source__type=NODE_TYPE_FARM,
    source__is_test=False,
    destination__is_test=False,
)
for prod in Product.objects.filter(
    batches__source_transaction__in=txns
).distinct():
    prod_txns = ExternalTransaction.objects.filter(
        source__type=NODE_TYPE_FARM,
        source__is_test=False,
        destination__is_test=False,
        result_batches__product=prod,
    )
    unq_currencies = get_unique_dict_list(
        prod_txns.values("currency").distinct()
    )
    for currency in unq_currencies:
        c_prod_txns = prod_txns.filter(
            currency=currency["currency"]
        ).distinct()
        total_qt = qs_sum(c_prod_txns, "_source_quantity")
        total_price = qs_sum(c_prod_txns, "price")
        print(
            "Product : ",
            prod,
            " currency :",
            currency["currency"],
            " total txns: ",
            c_prod_txns.count(),
            " Total quantity transacted : ",
            total_qt,
            " total base price paid excluding premium : ",
            total_price,
            "Avg price/unit: ",
            total_price / float(total_qt),
        )
