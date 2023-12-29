from v2.supply_chains.models import Node


def set_connection_is_test():
    """To perform function set_connection_is_test."""
    nodes = Node.objects.filter(is_test=True)
    for node in nodes:
        node.get_connections().update(is_test=True)


def run():
    """To perform function run."""
    set_connection_is_test()
