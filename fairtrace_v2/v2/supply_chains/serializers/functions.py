"""Serializers for node for consumer interface related APIs."""
from common import library as common_lib
from django.core.cache import cache
from django.utils import translation
from haversine import haversine
from v2.claims.constants import STATUS_APPROVED
from v2.supply_chains.models import Node


def get_node_claims(node):
    """returns node claims."""
    company_claims = []
    for claim in node.claims.filter(status=STATUS_APPROVED):
        claim_data = {
            "id": claim.idencode,
            "claim": {
                "id": claim.claim.idencode,
                "name": claim.claim.name,
                "description_basic": claim.claim.description_basic,
                "description_full": claim.claim.description_full,
                "type": claim.claim.type,
                "scope": claim.claim.scope,
            },
            "status": claim.status,
            "attached_by": {
                "id": claim.attached_by.idencode,
                "name": claim.attached_by.full_name,
                "type": claim.attached_by.type,
                "image": claim.attached_by.image_url,
            },
            "node": {
                "id": claim.node.idencode,
                "name": claim.node.full_name,
                "type": claim.node.type,
                "image": claim.node.image_url,
            },
        }
        if claim.verifier:
            claim_data["verifier"] = {
                "id": claim.verifier.idencode,
                "name": claim.verifier.full_name,
                "type": claim.verifier.type,
                "image": claim.verifier.image_url,
            }
        company_claims.append(claim_data)
    return company_claims


def clear_keys(search):
    """Clear cache using keys."""
    keys = cache.keys(search)
    cache.delete_many(keys)


def get_node_data(node=None, node_id=None, force_reload=False):
    """Returns node data."""
    if not force_reload:
        if not node_id:
            if not node:
                raise AssertionError(
                    "Either Node object or node_id is required"
                )
            try:
                node_id = node.id
            except Exception:
                raise AssertionError(
                    "Either Node object or node_id is required"
                )
        key = "node_basic_data_%s_%s" % (
            common_lib._encode(node_id),
            translation.get_language(),
        )
        node_data = cache.get(key)
        if node_data:
            return node_data
    if not node:
        try:
            node = Node.objects.get(id=node_id)
        except Exception:
            raise AssertionError("Either Node object or node_id is required")
    node_id = node.id
    key = "node_basic_data_%s_%s" % (
        common_lib._encode(node_id),
        translation.get_language(),
    )
    # To clear node data in all languages.
    clear_keys(f"node_basic_data_{common_lib._encode(node_id)}_*")

    nsc = node.nodesupplychain_set.filter(
        supply_chain=node.supply_chains.all().first()
    )
    primary_operation = {
        "id": None,
        "name": None,
    }
    if nsc and nsc[0].primary_operation:
        primary_operation["id"] = nsc[0].primary_operation.idencode
        primary_operation["name"] = nsc[0].primary_operation.name
    data = {
        "id": node.idencode,
        "name": node.full_name,
        "short_name": node.short_name,
        "blockchain_address": node.blockchain_key,
        "primary_operation": primary_operation,
        "type": node.type,
        "status": node.status,
        "image": node.image_url,
        "latitude": node.latitude,
        "longitude": node.longitude,
        "country": node.country,
        "province": node.province,
        "description_basic": node.description_basic,
        "date_joined": node.date_joined.timestamp()
        if node.date_joined
        else None,
        "managers": [i.idencode for i in node.managers.all()],
        "claims": get_node_claims(node),
    }
    cache.set(key, data, None)
    return data


def serialize_node_basic(
    node=None, node_id=None, force_reload=False, many=False
):
    """Serialize basic node details."""
    if node is None and node_id is None:
        raise AssertionError("Either Node object or node_id is required")

    if many:
        nodes = node if node else []
        node_ids = node_id if node_id else []
    else:
        nodes = [node] if node else []
        node_ids = [node_id] if node_id else []

    data = []
    for node_object in nodes:
        data.append(get_node_data(node_object, force_reload=force_reload))
    for nid in node_ids:
        data.append(get_node_data(node_id=nid, force_reload=force_reload))

    if many:
        return data
    else:
        return data[0]


def serialize_node_blockchain(node=None, node_id=None, force_reload=False):
    """Serialize node blockchain."""
    if not force_reload:
        if not node_id:
            try:
                node_id = node.id
            except Exception:
                raise AssertionError(
                    "Either Node object or node_id is required"
                )
        key = "node_blockchain_data_%s_%s" % (
            common_lib._encode(node_id),
            translation.get_language(),
        )
        node_data = cache.get(key)
        if node_data:
            return node_data
    if not node:
        try:
            node = Node.objects.get(id=node_id)
        except Exception:
            raise AssertionError("Either Node object or node_id is required")
    node_id = node.id
    key = "node_blockchain_data_%s_%s" % (
        common_lib._encode(node_id),
        translation.get_language(),
    )
    data = {
        "id": node.idencode,
        "name": node.short_name,
        "blockchain_address": node.blockchain_address,
        "latlong": {
            "id": node.idencode,
            "latitude": node.latitude,
            "longitude": node.longitude,
        },
    }
    cache.set(key, data, None)
    return data


def serialize_connection_buyer(connection=None, force_reload=False):
    """Serialize connection buyer."""
    if not connection:
        connection_data = {
            "parent_name": "",
            "parent_id": 0,
            "connection_status": 0,
            "distance": 0,
            "email_sent": True,
            "supplier_for": [],
            "buyer_for": [],
            "managers": [],
        }
        return connection_data
    key = f"connection_{connection.id}_buyerchain"
    if not force_reload:
        connection_data = cache.get(key)
        if connection_data:
            return connection_data
    buy_tags = [
        item.supplier_idencode for item in connection.supplier_tags.all()
    ]
    sup_tags = [item.buyer_idencode for item in connection.buyer_tags.all()]
    buyer_coord = (connection.buyer.latitude, connection.buyer.longitude)
    supplier_coord = (
        connection.supplier.latitude,
        connection.supplier.longitude,
    )
    distance = haversine(buyer_coord, supplier_coord)
    connection_data = {
        "parent_name": connection.supplier.full_name,
        "parent_id": connection.supplier.idencode,
        "connection_status": connection.status,
        "distance": distance,
        "email_sent": connection.invitation.email_sent,
        "supplier_for": sup_tags,
        "buyer_for": buy_tags,
        "managers": [
            {"id": i.idencode, "name": i.full_name}
            for i in connection.supplier.managers.all()
        ],
        # managers is an unrelated data point but is required when mapping
        # the connections.
    }
    cache.set(key, connection_data, None)
    return connection_data


def serialize_connection_supplier(connection=None, force_reload=False):
    """Serialize connection supplier."""
    if not connection:
        connection_data = {
            "parent_name": "",
            "parent_id": 0,
            "connection_status": 0,
            "distance": 0,
            "email_sent": True,
            "supplier_for": [],
            "buyer_for": [],
            "managers": [],
        }
        return connection_data
    key = f"connection_{connection.id}_supplierchain"
    if not force_reload:
        connection_data = cache.get(key)
        if connection_data:
            return connection_data
    sup_tags = [item.buyer_idencode for item in connection.buyer_tags.all()]
    buy_tags = [
        item.supplier_idencode for item in connection.supplier_tags.all()
    ]
    connection_data = {
        "parent_name": connection.buyer.full_name,
        "parent_id": connection.buyer.idencode,
        "connection_status": connection.status,
        "distance": connection.distance,
        "email_sent": connection.invitation.email_sent,
        "supplier_for": sup_tags,
        "buyer_for": buy_tags,
        "managers": [
            {"id": i.idencode, "name": i.full_name}
            for i in connection.buyer.managers.all()
        ],
    }
    cache.set(key, connection_data, None)
    return connection_data
