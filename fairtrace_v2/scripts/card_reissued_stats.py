from v2.projects.models import NodeCard
from v2.transactions.models import ExternalTransaction

MR_ID = 2144
TOKO_ID = 1432

toko_reissues = []
mr_reissues = []
for card in NodeCard.objects.all().exclude(node__isnull=True):
    first_txn = (
        ExternalTransaction.objects.filter(source=card.node)
        .order_by("created_on")
        .first()
    )

    if not first_txn:
        continue
    if card.updated_on > first_txn.created_on:
        if card.node.get_buyers().filter(id=MR_ID).exists():
            print("card reissues mr", card.node, card.node.get_buyers())
            mr_reissues.append(card.node)

        elif card.node.get_buyers().filter(id=TOKO_ID).exists():
            print("card reissues toko", card.node, card.node.get_buyers())
            toko_reissues.append(card.node)

print("MR guys")
for node in mr_reissues:
    print(node.full_name)

print("toko guys")

for node in toko_reissues:
    print(node.full_name)
