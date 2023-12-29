"""Graph models for the supply chain.

These models are not connected to the RDBMS, Postgres, but to the Neo4j
database. The approach uses is a skeletal approach to minimize the data
redundancy across multiple databases. Only very minimal information
required for querying is added to the graph. Any further information
required is then fetched from the RDBMS database. The ideology behind
the implementation is to speed up recursive queries in fetching the
connections of an actor.
"""
import neomodel
from django.utils import timezone
from django.utils.timezone import datetime
from neomodel import cardinality

from .cypher import BUYERS
from .cypher import construct_query
from .cypher import END_CONN
from .cypher import ROOT
from .cypher import START_CONN
from .cypher import SUPPLIERS
from .cypher import TAGS


class BaseStructuredNode(neomodel.StructuredNode):
    """Class to handle BaseStructuredNode and functions."""

    uid = neomodel.UniqueIdProperty()
    created_on = neomodel.DateTimeProperty(default=datetime.now)
    updated_on = neomodel.DateTimeProperty(default=datetime.now)

    __abstract_node__ = True

    def save(self):
        """To perform function save."""
        self.updated_on = timezone.now()
        super(BaseStructuredNode, self).save()


class BuyFromRel(neomodel.StructuredRel):
    """Class to handle BuyFromRel and functions."""

    created_on = neomodel.DateTimeProperty(default=datetime.now)
    supply_chain_id = neomodel.IntegerProperty()


class TagRel(neomodel.StructuredRel):
    """Class to handle TagRel and functions."""

    created_on = neomodel.DateTimeProperty(default=datetime.now)
    distance = neomodel.FloatProperty()
    tag_id = neomodel.IntegerProperty()
    supply_chain_id = neomodel.IntegerProperty()


class ConnectionGraphModel(BaseStructuredNode):
    """Graph connection model to store information about connections between
    nodes."""

    connection_id = neomodel.IntegerProperty(required=True)

    status = neomodel.IntegerProperty()
    email_sent = neomodel.BooleanProperty()
    supply_chain_id = neomodel.IntegerProperty()
    active = neomodel.BooleanProperty(default=True)
    distance = neomodel.FloatProperty()
    labels = neomodel.JSONProperty()

    supplier = neomodel.RelationshipTo(
        "NodeGraphModel",
        "BUYS_FROM",
        cardinality=cardinality.One,
        model=BuyFromRel,
    )
    buyer = neomodel.RelationshipFrom(
        "NodeGraphModel",
        "BUYS_FROM",
        cardinality=cardinality.One,
        model=BuyFromRel,
    )

    buyer_tag = neomodel.RelationshipTo(
        "ConnectionGraphModel", "BUYER_TAG", model=TagRel
    )
    supplier_tag = neomodel.RelationshipFrom(
        "ConnectionGraphModel", "BUYER_TAG", model=TagRel
    )

    def disconnect_all(self):
        """To perform function isconnect_all."""
        self.supplier.disconnect_all()
        self.buyer.disconnect_all()
        self.buyer_tag.disconnect_all()
        self.supplier_tag.disconnect_all()
        return True


class NodeGraphModel(BaseStructuredNode):
    """Graph node model to store minimal information about the node."""

    ft_node_id = neomodel.IntegerProperty()
    ft_node_idencode = neomodel.StringProperty(required=True)

    type = neomodel.IntegerProperty(required=True)
    full_name = neomodel.StringProperty(required=True)
    managers = neomodel.JSONProperty()

    suppliers = neomodel.RelationshipTo(
        "ConnectionGraphModel", "BUYS_FROM", model=BuyFromRel
    )
    buyers = neomodel.RelationshipFrom(
        "ConnectionGraphModel", "BUYS_FROM", model=BuyFromRel
    )

    def disconnect_all(self):
        """To perform function isconnect_all."""
        self.suppliers.disconnect_all()
        self.buyers.disconnect_all()
        return True

    def map_suppliers(
        self, supply_chain=None, start_connections=None, target_node=None
    ):
        """To perform function map_suppliers."""
        query = construct_query(
            source=self,
            relation=SUPPLIERS,
            supply_chain=supply_chain,
            start_connections=start_connections,
            target_node=target_node,
        )
        data, col = self.cypher(query)
        return data

    def map_buyers(
        self, supply_chain=None, start_connections=None, target_node=None
    ):
        """To perform function map_buyers."""
        query = construct_query(
            source=self,
            relation=BUYERS,
            supply_chain=supply_chain,
            start_connections=start_connections,
            target_node=target_node,
        )
        data, col = self.cypher(query)
        return data

    def search_suppliers(self, destination, supply_chain=None):
        """To perform function search_suppliers."""
        query = construct_query(
            source=self,
            relation=SUPPLIERS,
            supply_chain=supply_chain,
            target_node=destination,
        )

        data, col = self.cypher(query)
        connections = {}
        for chain_item in data:
            supply_chain_id = chain_item[END_CONN]["supply_chain_id"]
            end_conn = ConnectionGraphModel.inflate(chain_item[END_CONN])
            if supply_chain and supply_chain.id != supply_chain_id:
                continue
            path = []
            for tag_data in chain_item[TAGS]:
                tag = TagRel.inflate(tag_data)
                path.append(tag.end_node().buyer.single().ft_node_id)
            path.append(end_conn.buyer.single().ft_node_id)
            path.append(end_conn.supplier.single().ft_node_id)
            if supply_chain_id in connections:
                if len(path) >= len(connections[supply_chain_id]["path"]):
                    continue
            connections[supply_chain_id] = {
                "supply_chain_id": supply_chain_id,
                "connection_id": end_conn.connection_id,
                "path": path,
            }
        return list(connections.values())

    def search_buyers(self, destination, supply_chain=None):
        """To perform function search_buyers."""
        query = construct_query(
            source=self,
            relation=BUYERS,
            supply_chain=supply_chain,
            target_node=destination,
        )

        data, col = self.cypher(query)
        connections = {}
        for chain_item in data:
            supply_chain_id = chain_item[END_CONN]["supply_chain_id"]
            end_conn = ConnectionGraphModel.inflate(chain_item[END_CONN])
            if supply_chain and supply_chain.id != supply_chain_id:
                continue
            path = []
            for tag_data in chain_item[TAGS]:
                tag = TagRel.inflate(tag_data)
                path.append(tag.start_node().supplier.single().ft_node_id)
            path.append(end_conn.supplier.single().ft_node_id)
            path.append(end_conn.buyer.single().ft_node_id)
            if supply_chain_id in connections:
                if len(path) >= len(connections[supply_chain_id]["path"]):
                    continue
            connections[supply_chain_id] = {
                "supply_chain_id": supply_chain_id,
                "connection_id": end_conn.connection_id,
                "path": path,
            }
        return list(connections.values())

    def get_supplier_chain(
        self,
        supply_chain=None,
        include_self=False,
        fast_mode=False,
        start_connections=None,
    ):
        """Returns supplier chain."""
        chain_ids = []
        if include_self:
            chain_ids.append(self.ft_node_id)

        data = self.map_suppliers(supply_chain, start_connections)
        tier_data = {
            self.ft_node_id: {
                "iddecode": self.ft_node_id,
                "id": self.ft_node_idencode,
                "connected_to": {
                    0: {
                        "parent_name": "",
                        "parent_id": 0,
                        "connection_status": 0,
                        "email_sent": True,
                        "labels": [],
                        "supplier_for": [],
                        "buyer_for": [],
                        "managers": [],
                    }
                },
                "distance": 0,
                "tier": 0,
                "type": self.type,
            }
        }
        for chain_item in data:
            node_id = chain_item[ROOT]["ft_node_id"]
            chain_ids.append(node_id)
            type = chain_item[ROOT]["type"]
            tier = len(chain_item[TAGS]) + 1
            chain_start_dist = chain_item[START_CONN]["distance"]
            chain_end_dist = chain_item[END_CONN]["distance"]
            tag_distance = sum(i["distance"] for i in chain_item[TAGS])
            total_distance = (
                chain_start_dist + chain_end_dist
            ) / 2 + tag_distance

            if fast_mode:
                parent_id = 0
                parent_name = ""
                managers = []
                connection_status = 0
                email_sent = None
                labels = []
                supplier_for = []
                buyer_for = []
            else:
                conn_graph = ConnectionGraphModel.inflate(chain_item[END_CONN])
                parent = conn_graph.buyer.single()
                connection_status = conn_graph.status
                email_sent = conn_graph.email_sent
                labels = conn_graph.labels
                parent_id = parent.ft_node_idencode
                parent_name = parent.full_name
                managers = parent.managers
                supplier_for = [
                    i.buyer.single().ft_node_idencode
                    for i in conn_graph.buyer_tag.all()
                ]
                buyer_for = [
                    i.supplier.single().ft_node_idencode
                    for i in conn_graph.supplier_tag.all()
                ]

            item_data = {
                "iddecode": node_id,
                "id": chain_item[ROOT]["ft_node_idencode"],
                "connected_to": {
                    parent_id: {
                        "parent_name": parent_name,
                        "parent_id": parent_id,
                        "connection_status": connection_status,
                        "email_sent": email_sent,
                        "labels": labels,
                        "supplier_for": supplier_for,
                        "buyer_for": buyer_for,
                        "managers": managers,
                    }
                },
                "distance": total_distance,
                "tier": tier,
                "type": type,
            }
            if node_id not in tier_data:
                tier_data[node_id] = item_data
            else:
                if parent_id not in tier_data[node_id]["connected_to"]:
                    tier_data[node_id]["connected_to"][parent_id] = item_data[
                        "connected_to"
                    ][parent_id]
                tier_data[node_id]["distance"] = min(
                    total_distance, tier_data[node_id]["distance"]
                )
                tier_data[node_id]["tier"] = min(
                    tier, tier_data[node_id]["tier"]
                )
        for i in tier_data.keys():
            tier_data[i]["connected_to"] = list(
                tier_data[i]["connected_to"].values()
            )

        return list(set(chain_ids)), tier_data

    def get_buyer_chain(
        self,
        supply_chain=None,
        include_self=False,
        fast_mode=False,
        start_connections=None,
    ):
        """Returns buyer-chain."""
        chain_ids = []
        if include_self:
            chain_ids.append(self.ft_node_id)

        data = self.map_buyers(supply_chain, start_connections)
        tier_data = {
            self.ft_node_id: {
                "iddecode": self.ft_node_id,
                "id": self.ft_node_idencode,
                "connected_to": {
                    0: {
                        "parent_name": "",
                        "parent_id": 0,
                        "connection_status": 0,
                        "email_sent": None,
                        "labels": [],
                        "supplier_for": [],
                        "buyer_for": [],
                        "managers": [],
                    }
                },
                "distance": 0,
                "tier": 0,
                "type": self.type,
            }
        }
        for chain_item in data:
            node_id = chain_item[ROOT]["ft_node_id"]
            chain_ids.append(node_id)
            node_type = chain_item[ROOT]["type"]
            tier = -(len(chain_item[TAGS]) + 1)
            chain_start_dist = chain_item[START_CONN]["distance"]
            chain_end_dist = chain_item[END_CONN]["distance"]
            tag_distance = sum(i["distance"] for i in chain_item[TAGS])
            total_distance = (
                chain_start_dist + chain_end_dist
            ) / 2 + tag_distance

            if fast_mode:
                parent_id = 0
                parent_name = ""
                managers = []
                connection_status = 0
                email_sent = None
                labels = []
                supplier_for = []
                buyer_for = []
            else:
                conn_graph = ConnectionGraphModel.inflate(chain_item[END_CONN])
                parent = conn_graph.supplier.single()
                connection_status = conn_graph.status
                email_sent = conn_graph.email_sent
                labels = conn_graph.labels
                parent_id = parent.ft_node_idencode
                parent_name = parent.full_name
                managers = parent.managers
                supplier_for = [
                    i.buyer.single().ft_node_idencode
                    for i in conn_graph.buyer_tag.all()
                ]
                buyer_for = [
                    i.supplier.single().ft_node_idencode
                    for i in conn_graph.supplier_tag.all()
                ]

            item_data = {
                "iddecode": node_id,
                "id": chain_item[ROOT]["ft_node_idencode"],
                "connected_to": {
                    parent_id: {
                        "parent_name": parent_name,
                        "parent_id": parent_id,
                        "connection_status": connection_status,
                        "email_sent": email_sent,
                        "labels": labels,
                        "supplier_for": supplier_for,
                        "buyer_for": buyer_for,
                        "managers": managers,
                    }
                },
                "distance": total_distance,
                "tier": tier,
                "type": node_type,
            }
            if node_id not in tier_data:
                tier_data[node_id] = item_data
            else:
                if parent_id not in tier_data[node_id]["connected_to"]:
                    tier_data[node_id]["connected_to"][parent_id] = item_data[
                        "connected_to"
                    ][parent_id]
                tier_data[node_id]["distance"] = min(
                    total_distance, tier_data[node_id]["distance"]
                )
                tier_data[node_id]["tier"] = min(
                    tier, tier_data[node_id]["tier"]
                )
        for i in tier_data.keys():
            tier_data[i]["connected_to"] = list(
                tier_data[i]["connected_to"].values()
            )

        return list(set(chain_ids)), tier_data
