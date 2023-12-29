from v2.supply_chains.models import Farmer
from v2.transactions.models import ExternalTransaction

NODE_TYPE_FARM = 2
node = None
for tx in ExternalTransaction.objects.filter(destination=node):
    if tx.source.type != NODE_TYPE_FARM:
        continue
    if tx.source.description_basic:
        continue
    farmer = Farmer.objects.get(id=tx.source.id)
    desc = (
        f"{farmer.first_name} received a payment of around $4 per kg of"
        " roasted coffee. By paying $5,80 per kg of roasted coffee we made"
        " sure the cooperatives of farmers were profitable on this contract."
    )
    tx.source.description_basic = desc
    tx.source.save()
