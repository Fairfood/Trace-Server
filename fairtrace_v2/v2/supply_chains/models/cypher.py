"""Raw cypher queries used for fetching data from Neo4j."""

CYPHER_BASE_QUERY = (
    "MATCH (source:NodeGraphModel {{uid: '{source.uid}'}}){}"
    "[rel_start:BUYS_FROM]{}"
    "(conn_start:ConnectionGraphModel "
    "{supply_chain_filter}){}[tags:BUYER_TAG*0..]{}"
    "(conn_end:ConnectionGraphModel){}[rel_end:BUYS_FROM]{}"
    "(root:NodeGraphModel {target_node_filter})"
    "{where_conditions}"
    "RETURN DISTINCT root, conn_start, conn_end, tags"
)
# Relations
SUPPLIERS = 1
BUYERS = 2

# Relation Directions
SUPPLIER_RELATION_DIRECIONS = ("-", "->", "<-", "-", "-", "->")
BUYER_RELATION_DIRECIONS = ("<-", "-", "-", "->", "<-", "-")

# Return data positions
ROOT = 0
START_CONN = 1
END_CONN = 2
TAGS = 3


def construct_query(
    source,
    relation,
    supply_chain=None,
    target_node=None,
    start_connections=None,
):
    """Construct query for graph data fetch."""
    supply_chain_filter = (
        "{supply_chain_id: %d}" % supply_chain.id if supply_chain else ""
    )
    target_node_filter = "{uid: '%s'}" % target_node.uid if target_node else ""
    where_conditions = ""
    if relation == SUPPLIERS:
        directions = SUPPLIER_RELATION_DIRECIONS
    else:
        directions = BUYER_RELATION_DIRECIONS
    conditions = []
    if start_connections is not None:
        uids = [c.graph_uid for c in start_connections]
        conditions.append("conn_start.uid in ['{}']".format("', '".join(uids)))
    if conditions:
        where_conditions = "WHERE " + " and ".join(conditions)
    cypher_base = CYPHER_BASE_QUERY.format(
        *directions,
        source=source,
        supply_chain_filter=supply_chain_filter,
        target_node_filter=target_node_filter,
        where_conditions=where_conditions,
    )

    return cypher_base
