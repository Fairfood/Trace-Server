from common.drf_custom.serializers import DynamicModelSerializer
from common.exceptions import BadRequest
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from v2.supply_chains.models.profile import FarmerAttachment
from v2.supply_chains.models.profile import FarmerPlot
from v2.supply_chains.models.profile import FarmerReference
from v2.supply_chains.models.profile import Reference
from v2.supply_chains.serializers.node import NodeSerializer


class ReferenceSerializer(DynamicModelSerializer):
    """To handle Reference model serialization."""

    class Meta:
        model = Reference
        fields = "__all__"


class FarmerReferenceSerializer(DynamicModelSerializer):
    """To handle FarmerReference model serialization."""

    reference_details = ReferenceSerializer(
        source="reference",
        read_only=True,
        fields=("id", "name", "image", "description", "is_editable"),
    )
    source_details = NodeSerializer(
        source="source", read_only=True, fields=("id", "full_name")
    )

    class Meta:
        model = FarmerReference
        fields = "__all__"
    
    def validate(self, attrs):
        node = self.context["view"].kwargs["node"]
        suppliers = node.map_supplier_pks()
        buyers = node.map_buyer_pks()
        ids = list(suppliers)+list(buyers)
        if FarmerReference.objects.filter(
            number=attrs['number'], 
            farmer__node_ptr__in=ids).exists():
            raise BadRequest("Identification Number Already Exists!")
        return super().validate(attrs)


class FarmerPlotSerializer(DynamicModelSerializer):
    """To handle FarmerPlot model serialization."""

    farmer_details = NodeSerializer(
        source="farmer", read_only=True, fields=("id", "full_name")
    )

    class Meta:
        model = FarmerPlot
        fields = "__all__"
    
    def update(self, instance, validated_data):
        instance.sync_with_navigate = False
        return super().update(instance, validated_data)


class FarmerAttachmentSerializer(DynamicModelSerializer):
    """To handle FarmerAttachments model serialization."""

    node_details = NodeSerializer(
        source="node", read_only=True, fields=("id", "full_name")
    )
    creator_name = serializers.SerializerMethodField()

    class Meta:
        model = FarmerAttachment
        fields = "__all__"

    def get_creator_name(self, instance):
        """Returns creator name."""
        return instance.creator.get_full_name() if instance.creator else None
