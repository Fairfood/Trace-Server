from celery.task import task
from common.cache import filesystem_cache
from django.apps import apps
from v2.reports.constants import FARMER
from v2.supply_chains.serializers.supply_chain import MapConnectionsSerializer


def _get_cached_keys(nodes):
    """Get only cached keys from the set of nodes."""
    cache = filesystem_cache
    keys = []
    for node in nodes.iterator():
        keys.extend(cache.keys(f"connection_{node.id}_*"))
    return keys


@task(name="rebuild_connection_cache", queue="high")
def _rebuild_cache(keys):
    """delete and rebuild cache with the keys."""
    serializer_class = MapConnectionsSerializer
    for key in keys:
        # format of the key is as the following,
        # 'connection_{node_id}_{supply_chain_id}_{language_code}'.
        _split = key.split("_")
        node_id = _split[1]
        supply_chain = _split[2]
        node = apps.get_model("supply_chains", "Node").objects.get(pk=node_id)
        serializer = serializer_class(node)
        data = serializer.to_representation(node, sc_id=supply_chain)
        filesystem_cache.set(key, data)


def clear_connection_cache(node_id):
    """This will clear the connection cache and rebuild it."""
    node = apps.get_model("supply_chains", "Node").objects.get(pk=node_id)
    suppliers = (
        node.get_supplier_chain(include_self=True)[0]
        .exclude(type=FARMER)
        .only("id")
    )
    buyers = node.get_buyer_chain()[0].exclude(type=FARMER).only("id")
    connections = suppliers | buyers
    keys = _get_cached_keys(connections)
    _rebuild_cache.delay(keys)
