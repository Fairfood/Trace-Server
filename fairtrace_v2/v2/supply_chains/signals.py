from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .cache_resetters import reload_related_statistics
from .models import Connection
from .models import ConnectionTag
from .models import Node


@receiver(pre_delete, sender=Node)
def delete_node_graph_node(sender, instance, **kwargs):
    """To perform function lete_node_graph_node."""
    graph_node = instance.graph_node
    if graph_node:
        graph_node.disconnect_all()
        graph_node.delete()
    return True


@receiver(pre_delete, sender=Connection)
def delete_connection_graph_node(sender, instance, **kwargs):
    """To perform function lete_connection_graph_node."""
    reload_related_statistics.delay(instance.supplier.id)
    reload_related_statistics.delay(instance.buyer.id)
    graph_node = instance.graph_node
    if graph_node:
        graph_node.disconnect_all()
        graph_node.delete()
    return True


@receiver(pre_delete, sender=ConnectionTag)
def delete_connection_tag_rel(sender, instance, **kwargs):
    """To perform function lete_connection_tag_rel."""
    try:
        tag_rel = (
            instance.buyer_connection.graph_node.supplier_tag.relationship(
                instance.supplier_connection.graph_node
            )
        )
        tag_rel.delete()
    except Exception:
        return False


# NOTE: Do manual update while updating Nodes.
# @receiver(post_save)
# def caching_signal_supply_chain(sender, instance, **kwargs):
#     sender_name = sender.__name__
#     batches = []
#     if sender_name == 'Node':
#         batches = instance.batches.all()
#     elif sender_name in ['Company', 'Farmer']:
#         update_fields = (list(kwargs['update_fields'])
#                          if kwargs['update_fields']
#                          else [])
#         # To bypass member node setting in api call.
#         if ['active'] != update_fields:
#             batches = Batch.objects.filter(node_id=instance.id)
#     for batch in batches:
#         cache_handlers.terminate_active_tasks(batch.id, 'clear-ci-map-cache')
#         cache_handlers.clear_ci_map_cache.delay(batch.id)
#         cache_handlers.terminate_active_tasks(batch.id,
#         'clear-ci-stage-cache')
#         cache_handlers.clear_ci_stage_cache.delay(batch.id)
#         cache_handlers.terminate_active_tasks(batch.id, '
#         clear-ci-claim-cache')
#         cache_handlers.clear_ci_claim_cache.delay(batch.id)


# @receiver(post_save)
# def connection_cache_resetting_signal(sender, instance, **kwargs):
#     sender_name = sender.__name__
#     node = None
#     if sender_name == 'Connection':
#         # Expecting buyer node also in the chain
#         node = instance.supplier
#     if sender_name in ['Node', 'Farmer', 'Company']:
#         update_fields = (list(kwargs['update_fields'])
#                          if kwargs['update_fields']
#                          else [])
#         if ['active'] != update_fields:
#             if not kwargs['created']:
#                 node = instance
#     if node:
#         clear_connection_cache(node.id)
