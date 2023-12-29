from common import library as comm_lib
from common.drf_custom import fields as custom_fields
from rest_framework import serializers
from v2.supply_chains.models import BlockchainWallet
from v2.supply_chains.models import Node
from v2.supply_chains.models import Operation
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.serializers.functions import serialize_node_basic


class SupplyChainSerializer(serializers.ModelSerializer):
    """Serializer for SupplyChains."""

    id = custom_fields.IdencodeField()

    class Meta:
        """Meta Data."""

        model = SupplyChain
        fields = ("id", "name", "description", "image")


class OperationSerializer(serializers.ModelSerializer):
    """Serializer for Operations."""

    id = custom_fields.IdencodeField(read_only=True)
    name = serializers.CharField()

    class Meta:
        model = Operation
        fields = ("id", "name", "node_type")


class NodeBasicSerializer(serializers.ModelSerializer):
    """Serializer for Node model.

    Used as base for Farmer and Company
    """

    tier_data: dict = {}
    pseudonymize = False
    can_manage = False

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        self.pseudonymize = kwargs.pop("pseudonymize", False)
        self.tier_data = kwargs.pop("tier_data", {})
        self.can_manage = kwargs.pop("can_manage", False)
        super(NodeBasicSerializer, self).__init__(*args, **kwargs)

    class Meta:
        """Meta data."""

        model = Node

    def get_blockchain_address(self, instance):
        """To perform function get_blockchain_address."""
        if instance.blockchain_account:
            return instance.blockchain_account.public
        else:
            return ""

    def to_representation(self, instance):
        """To perform function to_representation."""
        data = serialize_node_basic(instance)
        if instance.is_company():
            data["email_sent"] = instance.email_sent
        else:
            data["email_sent"] = False
        if self.tier_data:
            data["tier"] = self.tier_data[instance.id]["tier"]
            data["connected_to"] = self.tier_data[instance.id]["connected_to"]
            email_sent_check = [
                i.pop("email_sent") for i in data["connected_to"]
            ]
            data["email_sent"] = all(email_sent_check)

        data["add_connections"] = False
        data["pseudonimized"] = False
        data["add_connections"] = self.can_manage
        if self.pseudonymize:
            data["pseudonimized"] = True
            hidden_fields = instance.get_hidden_fields()
            if "connected_to" in data:
                for parent in data["connected_to"]:
                    parent["parent_name"] = comm_lib._pseudonymize_data(
                        parent["parent_name"], "parent_name"
                    )
            comm_lib._pop_out_from_dictionary(
                data, ["members", "hidden_fields", "documents"]
            )
            for field in hidden_fields:
                try:
                    data[field] = comm_lib._pseudonymize_data(
                        field, data[field]
                    )
                except KeyError:
                    pass
        return data


class NodeWalletSerializer(serializers.ModelSerializer):
    """Serializer for blockchain wallet."""

    id = custom_fields.IdencodeField()

    class Meta:
        model = BlockchainWallet
        fields = (
            "id",
            "account_id",
            "public",
            "wallet_type",
            "default",
            "explorer_url",
        )
