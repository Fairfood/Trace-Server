"""Serializers for connection request related APIs."""
from common.drf_custom import fields as custom_fields
from common.exceptions import BadRequest
from rest_framework import serializers
from v2.supply_chains.models import Connection
from v2.supply_chains.models import Node
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.supply_chains.serializers.public import SupplyChainSerializer
from v2.transparency_request import constants
from v2.transparency_request.models import ConnectionRequest


class ConnectionRequestSerializer(serializers.ModelSerializer):
    """Serializer for creating.

    retrieving and updating connection requests
    """

    id = custom_fields.IdencodeField(read_only=True)
    number = serializers.IntegerField(read_only=True)
    status = serializers.IntegerField(required=False)
    response = serializers.CharField(required=False)
    node = custom_fields.IdencodeField(
        related_model=Node, source="requestee", write_only=True
    )
    requester = custom_fields.IdencodeField(
        serializer=NodeBasicSerializer, read_only=True
    )
    requestee = custom_fields.IdencodeField(
        serializer=NodeBasicSerializer, read_only=True
    )
    supply_chain = custom_fields.IdencodeField(
        related_model=SupplyChain, serializer=SupplyChainSerializer
    )

    class Meta:
        model = ConnectionRequest
        fields = (
            "id",
            "request_type",
            "number",
            "status",
            "node",
            "supply_chain",
            "note",
            "created_on",
            "requester",
            "requestee",
            "response",
            "updated_on",
        )

    def create(self, validated_data):
        """To perform function create."""
        current_node = self.context["view"].kwargs["node"]
        validated_data["requester"] = current_node
        if not current_node.is_directly_connected_to(
            validated_data["requestee"],
            supply_chain=validated_data["supply_chain"],
        ):
            raise serializers.ValidationError(
                "You are not connected to"
                f" {validated_data['requestee'].full_name} in"
                f" {validated_data['supply_chain'].name} supply chain. Cannot"
                " send request"
            )
        conn_request = super(ConnectionRequestSerializer, self).create(
            validated_data
        )
        conn_request.log_activity()
        conn_request.notify()
        try:
            connection = Connection.objects.get(
                buyer=validated_data["requester"],
                supplier=validated_data["requestee"],
                supply_chain=validated_data["supply_chain"],
            )
            connection.update_graph_node()
        except Connection.DoesNotExist:
            raise BadRequest(
                "Node is not connected to"
                f" {validated_data['requestee'].full_name} in the"
                f" {validated_data['supply_chain']} supplychain."
            )
        return conn_request

    def update(self, instance, validated_data):
        """To perform function update."""
        if instance.status in [
            constants.TRANSPARENCY_REQUEST_STATUS_ACKNOWLEDGED,
            constants.TRANSPARENCY_REQUEST_STATUS_DECLINED,
        ]:
            raise BadRequest(
                "Status cannot be changed for already Acknowledged/Declined"
                " requests"
            )

        if validated_data["status"] in [
            constants.TRANSPARENCY_REQUEST_STATUS_DECLINED,
        ]:
            instance.reject(validated_data["response"])
            instance.save()
        elif validated_data["status"] in [
            constants.TRANSPARENCY_REQUEST_STATUS_ACKNOWLEDGED,
        ]:
            instance.status = validated_data["status"]
            instance.save()
        else:
            raise BadRequest(
                "Status can only be changed to Acknowledged or Declined"
            )
        return instance
