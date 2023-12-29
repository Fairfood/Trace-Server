"""Serializers related to dashboard."""
from common import library as comm_lib
from common.drf_custom import fields as custom_fields
from django.db.models import Count
from django.db.models import Q
from django.db.models import Sum
from rest_framework import serializers
from v2.claims.constants import STATUS_APPROVED
from v2.claims.models import Claim
from v2.dashboard.models import NodeStats
from v2.products import constants as prod_constants
from v2.products.models import Product
from v2.products.serializers import product as prod_serializers
from v2.supply_chains import constants as sc_constants
from v2.supply_chains.models import Label
from v2.supply_chains.models import Node
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.serializers import supply_chain as sc_serializers
from v2.supply_chains.serializers.node import OperationSerializer

# from v2.supply_chains.cache_resetters import reload_statistics


class NodeStatsSerializer(serializers.ModelSerializer):
    """Serialize node stats."""

    chain_length = serializers.IntegerField()

    class Meta:
        model = NodeStats
        fields = (
            "last_updated",
            "is_outdated",
            "supply_chain_count",
            "tier_count",
            "chain_length",
            "actor_count",
            "farmer_count",
            "supplier_count",
            "company_count",
            "traceable_chains",
            "invited_actor_count",
            "mapped_actor_count",
            "active_actor_count",
            "pending_invite_count",
            "operation_stats",
            "traceable_chain_percent",
            "farmer_coorinates",
            "supplier_coorinates",
            "buyer_ids",
            "supplier_ids",
            "farmer_ids",
        )


class NodeSupplyChainStatsSerializer(serializers.ModelSerializer):
    """Serialize supply chain node stats."""

    id = custom_fields.IdencodeField(source="supply_chain.id")
    name = serializers.CharField(source="supply_chain.name")
    chain_length = serializers.IntegerField()
    primary_operation = custom_fields.IdencodeField(
        serializer=OperationSerializer, required=False, allow_null=True
    )

    class Meta:
        model = NodeSupplyChain
        fields = (
            "id",
            "name",
            "complexity",
            "traceable",
            "tier_count",
            "chain_length",
            "actor_count",
            "farmer_count",
            "supplier_count",
            "company_count",
            "invited_actor_count",
            "mapped_actor_count",
            "active_actor_count",
            "pending_invite_count",
            "operation_stats",
            "farmer_coorinates",
            "supplier_coorinates",
            "buyer_ids",
            "supplier_ids",
            "farmer_ids",
            "primary_operation",
        )


class StatsSerializer(serializers.ModelSerializer):
    """Serializer to fetch informations to be shown in the dashboard."""

    # supply_chains = custom_fields.ManyToManyIdencodeField(
    #     serializer=sc_serializers.SupplyChainSerializer)
    actions = serializers.ListField(source="get_actions", read_only=True)
    chains_with_stock = serializers.SerializerMethodField("check_stock_status")

    supply_chain = None  # To store selected supply chain after initialization
    labels = None  # Filter applied in terms of labels
    suppliers = None
    buyers = None
    supplier_tier_data = None
    buyer_tier_data = None
    buyer_ids = None
    supplier_ids = None
    farmer_ids = None

    class Meta:
        model = Node
        fields = ("actions", "chains_with_stock")

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        super(StatsSerializer, self).__init__(*args, **kwargs)
        try:
            sc_id = comm_lib._decode(
                self.context["request"].query_params.get("supply_chain", None)
            )
            self.supply_chain = SupplyChain.objects.get(id=sc_id)
        except Exception:
            pass
        try:
            encoded_label_ids = self.context["request"].query_params.get(
                "labels", None
            )
            label_ids = [
                comm_lib._decode(i) for i in encoded_label_ids.split(",")
            ]
            self.labels = Label.objects.filter(id__in=label_ids)
        except Exception:
            pass

    def check_stock_status(self, node):
        """To perform function check_stock_status."""
        remaining_bathes = node.batches.filter(current_quantity__gt=0)
        if self.supply_chain:
            remaining_bathes = remaining_bathes.filter(
                product__supply_chain=self.supply_chain
            )
        supply_chains = []
        for supply_chain in (
            SupplyChain.objects.filter(products__batches__in=remaining_bathes)
            .order_by("name")
            .distinct("name")
        ):
            supply_chain_data = sc_serializers.SupplyChainSerializer(
                supply_chain
            ).data
            supply_chains.append(supply_chain_data)
        return supply_chains

    def check_connection_status(self, node):
        """To perform function check_connection_status."""
        farmer_chains = []
        farmer_ids = []

        company_chains = []
        company_ids = []

        all_supply_chains = []
        all_supply_chain_ids = []

        if self.supply_chain:
            supply_chains = [self.supply_chain]
        else:
            supply_chains = node.supply_chains.all().order_by("name")

        for supply_chain in supply_chains:
            suppliers = node.get_suppliers(supply_chain=supply_chain)
            farmers = suppliers.filter(type=sc_constants.NODE_TYPE_FARM)
            companies = suppliers.filter(type=sc_constants.NODE_TYPE_COMPANY)
            supply_chain_data = sc_serializers.SupplyChainSerializer(
                supply_chain
            ).data
            all_supply_chains.append(supply_chain_data)
            all_supply_chain_ids.append(supply_chain_data["id"])
            if farmers.exists():
                farmer_chains.append(supply_chain_data)
                farmer_ids.append(supply_chain_data["id"])
            if companies.exists():
                company_chains.append(supply_chain_data)
                company_ids.append(supply_chain_data["id"])
        incomplete_chain_ids = list(
            set(all_supply_chain_ids) - set(farmer_ids) - set(company_ids)
        )
        incomplete_chains = [
            i for i in all_supply_chains if i["id"] in incomplete_chain_ids
        ]
        return farmer_chains, company_chains, incomplete_chains

    def get_supply_chain_actors(self):
        """To perform function get_supply_chain_actors."""
        node_ids = [i.id for i in self.suppliers] + [i.id for i in self.buyers]
        total = Node.objects.filter(id__in=node_ids)
        tier_data = {}
        comp_tier_data = {}
        for node_id, tier in self.supplier_tier_data.items():
            increment = (
                1 if tier["type"] == sc_constants.NODE_TYPE_COMPANY else 0
            )
            if tier["tier"] not in tier_data:
                tier_data[tier["tier"]] = 1
                comp_tier_data[tier["tier"]] = increment
            else:
                tier_data[tier["tier"]] += 1
                comp_tier_data[tier["tier"]] += increment
        for node_id, tier in self.buyer_tier_data.items():
            increment = (
                1 if tier["type"] == sc_constants.NODE_TYPE_COMPANY else 0
            )
            if tier["tier"] not in tier_data:
                tier_data[tier["tier"]] = 1
                comp_tier_data[tier["tier"]] = increment
            else:
                tier_data[tier["tier"]] += 1
                comp_tier_data[tier["tier"]] += increment
        tier_data.pop(0)
        comp_tier_data.pop(0)
        return total.distinct("id"), tier_data, comp_tier_data

    def get_total_actors(self, node):
        """To perform function get_total_actors."""
        tier_data = {}
        (
            sc_actors,
            sc_tier_data,
            comp_tier_data,
        ) = self.get_supply_chain_actors()
        actor_ids = [i.id for i in sc_actors]
        for tier, count in comp_tier_data.items():
            check = tier in tier_data
            if check:
                tier_data[tier] += count
            else:
                tier_data[tier] = count
        actor_count = {"total": len(set(actor_ids)), "tier": tier_data}
        return actor_count

    def get_supply_chain_farmers(self):
        """To perform function get_supply_chain_farmers."""
        farmers = self.suppliers.exclude(
            type=sc_constants.NODE_TYPE_COMPANY
        ).distinct("id")
        return farmers

    def get_farmers(self, node):
        """To perform function get_farmers."""
        farmers = self.get_supply_chain_farmers()
        farmers_data = farmers.distinct("id").values("latitude", "longitude")
        return farmers_data

    def get_supply_chain_suppliers(self):
        """To perform function get_supply_chain_suppliers."""
        suppliers = self.suppliers.exclude(
            type=sc_constants.NODE_TYPE_FARM
        ).distinct("id")
        return suppliers

    def get_suppliers(self, node):
        """To perform function get_suppliers."""
        suppliers = self.get_supply_chain_suppliers()
        suppliers_data = suppliers.distinct("id").values(
            "latitude", "longitude"
        )
        return suppliers_data

    def get_product_claims(self, node):
        """To perform function get_product_claims."""
        claims = {}
        node_batches = node.batches.filter(current_quantity__gt=0)
        if self.supply_chain:
            node_batches = node_batches.filter(
                product__supply_chain=self.supply_chain
            )
        all_claims = Claim.objects.filter(
            attachedclaim__attachedbatchclaim__batch__in=node_batches
        ).annotate(
            total=Count("attachedclaim__attachedbatchclaim__batch"),
            verified=Count(
                "attachedclaim__attachedbatchclaim__batch",
                filter=Q(
                    attachedclaim__attachedbatchclaim__status=STATUS_APPROVED
                ),
            ),
        )
        for claim in all_claims:
            if claim.reference not in claims:
                claims[claim.reference] = {
                    "id": claim.idencode,
                    "name": claim.name,
                    "type": claim.type,
                    "scope": claim.scope,
                    "count": claim.total,
                    "verified": claim.verified,
                }
            else:
                claims[claim.reference]["count"] += claim.total
                claims[claim.reference]["verified"] += claim.verified
        return claims.values()

    def get_company_claims(self, node):
        """To perform function get_company_claims."""
        claims = {}
        supplier_ids = self.supplier_ids + [node.id]
        suppliers = Node.objects.filter(id__in=supplier_ids)
        all_claims = Claim.objects.filter(
            attachedclaim__attachedcompanyclaim__node__in=suppliers
        ).annotate(
            verified=Count(
                "attachedclaim__attachedcompanyclaim__node",
                filter=Q(
                    attachedclaim__attachedcompanyclaim__status=STATUS_APPROVED
                ),
            )
        )
        for claim in all_claims:
            if claim.reference not in claims:
                claims[claim.reference] = {
                    "id": claim.idencode,
                    "name": claim.name,
                    "type": claim.type,
                    "scope": claim.scope,
                    "count": len(self.supplier_ids),
                    "verified": claim.verified,
                }
            else:
                claims[claim.reference]["count"] += claim.total
                claims[claim.reference]["verified"] += claim.verified
        return claims.values()

    def get_stock(self, node):
        """To perform function get_stock."""
        products = Product.objects.filter(batches__node=node)
        if self.supply_chain:
            products = products.filter(supply_chain=self.supply_chain)
        products = products.annotate(
            quantity=Sum("batches__current_quantity")
        ).filter(quantity__gt=0)
        product_data = []
        for product in products:
            data = prod_serializers.ProductSerializer(product).data
            data["quantity"] = product.quantity
            data["unit"] = prod_constants.UNIT_KG
            product_data.append(data)
        return product_data

    def to_representation(self, node):
        """To perform function to_representation."""
        stats = super(StatsSerializer, self).to_representation(node)

        stats["selected_supply_chain"] = "all"
        if self.supply_chain:
            stats["selected_supply_chain"] = self.supply_chain.idencode

        stats_obj, created = NodeStats.objects.get_or_create(node=node)
        if (created or stats_obj.is_outdated) and not self.labels:
            stats_obj.update_values()
            # reload_statistics.delay(stats_obj.id)
        node_stats = NodeStatsSerializer(stats_obj).data
        stats["supply_chain_stats"] = []
        if self.supply_chain:
            node_supply_chain = node.nodesupplychain_set.get(
                supply_chain=self.supply_chain
            )
            if self.labels:
                sc_node_stats = node_supply_chain.get_stats_values(
                    labels=self.labels
                )
            else:
                sc_node_stats = NodeSupplyChainStatsSerializer(
                    node_supply_chain
                ).data
            for key, val in sc_node_stats.items():
                node_stats[key] = val
        else:
            overview = NodeSupplyChainStatsSerializer(
                node.nodesupplychain_set.all(), many=True
            ).data
            overview = sorted(
                overview, key=lambda i: i["complexity"], reverse=True
            )
            c = 1
            for sc in overview:
                sc["complexity_value"] = sc["complexity"]
                sc["complexity"] = c
                c += 1
            stats["supply_chain_overview"] = overview
        stats["farmers"] = node_stats.pop("farmer_coorinates")
        stats["suppliers"] = node_stats.pop("supplier_coorinates")
        stats["statistics"] = node_stats

        self.buyer_ids = node_stats.pop("buyer_ids")
        self.supplier_ids = node_stats.pop("supplier_ids")
        self.farmer_ids = node_stats.pop("farmer_ids")

        stats["products"] = self.get_stock(node)
        stats["product_claims"] = self.get_product_claims(node)
        stats["company_claims"] = self.get_company_claims(node)

        (
            stats["farmer_chains"],
            stats["supplier_chains"],
            stats["incomplete_chains"],
        ) = self.check_connection_status(node)
        return stats
