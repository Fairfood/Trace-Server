from celery import shared_task
from v2.dashboard.models import NodeStats
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.models import Node


@shared_task(name="reload_related_statistics", queue="low")
def reload_related_statistics(node_id):
    """Reload related statistics."""
    node = Node.objects.get(id=node_id)
    print(f"Flagging  stats of connections of {node.full_name}")
    buyer_chain, tier_data = node.get_buyer_chain()
    if buyer_chain:
        buyer_chain = buyer_chain.filter(type=NODE_TYPE_COMPANY)
    for actor in buyer_chain:
        stats, created = NodeStats.objects.get_or_create(node=actor)
        stats.outdate(outdated_by=node)
    supplier_chain, tier_data = node.get_supplier_chain()
    supplier_chain = supplier_chain.filter(type=NODE_TYPE_COMPANY)
    for actor in supplier_chain:
        stats, created = NodeStats.objects.get_or_create(node=actor)
        stats.outdate(outdated_by=node)
    print(f"Flagging  stats of connections of {node.full_name} complete.")
