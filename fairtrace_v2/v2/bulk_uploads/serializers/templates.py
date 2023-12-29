from rest_framework import serializers

from common.drf_custom.fields import RelatedIdencodeField
from common.drf_custom.serializers import DynamicModelSerializer
from django.db import transaction as dj_transaction

from .uploads import DataSheetUploadSerializer
from .. import constants
from ..models import DataSheetTemplate
from ..models import DataSheetTemplateField
from ..models import NodeDataSheetTemplates
from ..schemas.farmer_upload_schema import FarmerUploadSchema
from ..schemas.transaction_upload_schema import TransactionUploadSchema
from ...products.serializers.product import ProductSerializer
from ...supply_chains.models import Node


class DataSheetTemplateFieldSerializer(DynamicModelSerializer):
    """Serializer for the DataSheetTemplateField model.

    This serializer provides serialization and deserialization
    functionality for instances of the DataSheetTemplateField model. It
    includes all fields of the DataSheetTemplateField model.
    """
    label = serializers.SerializerMethodField()

    class Meta:
        model = DataSheetTemplateField
        fields = "__all__"

    @staticmethod
    def get_label(obj):
        return obj.name.replace("_", " ").title()


class DataSheetTemplateSerializer(DynamicModelSerializer):
    """Serializer for the DataSheetTemplate model.

    This serializer provides serialization and deserialization
    functionality for instances of the DataSheetTemplate model. It
    includes the DataSheetTemplateFieldSerializer for the
    'field_details' field (read-only) and 'fields' field (write-only).
    The 'field_details' field represents the detailed information of the
    fields associated with the template, while the 'fields' field is
    used for creating or updating the fields of the template. The
    serializer includes all fields of the DataSheetTemplate model.
    """
    node = RelatedIdencodeField(write_only=True, required=False,
                                queryset=Node.objects.all())
    field_details = DataSheetTemplateFieldSerializer(
        source="fields",
        many=True,
        read_only=True,
        exclude_fields=("template",),
    )
    fields = DataSheetTemplateFieldSerializer(
        many=True,
        write_only=True,
        required=False,
        exclude_fields=("template",)
    )
    is_system_template = serializers.BooleanField(read_only=True)
    latest_upload = serializers.SerializerMethodField()
    product_details = ProductSerializer(source="product", read_only=True,
                                        fields=("id", "name"))

    class Meta:
        model = DataSheetTemplate
        fields = "__all__"

    @dj_transaction.atomic
    def create(self, validated_data):
        """Create the template and its fields. Also link the node.

        This method is responsible for creating a new DataSheetTemplate
        instance along with its associated fields. The fields are
        provided in the 'fields' attribute of the validated_data. The
        method also links the template to a node if available.
        """
        fields = validated_data.pop("fields", [])
        node = validated_data.pop("node", None)
        instance = super().create(validated_data)
        self._create_fields(instance, fields)
        self._create_upload(instance, node)
        self._create_node_template(instance, node)
        return instance

    @dj_transaction.atomic
    def update(self, instance, validated_data):
        """Update the template and its fields. Also link the node.

        This method is responsible for updating an existing
        DataSheetTemplate instance along with its associated fields. The
        fields are provided in the 'fields' attribute of the
        validated_data. The existing fields associated with the instance
        are deleted before creating the new fields. The method also
        links the template to a node if available.
        """
        fields = validated_data.pop("fields", [])
        node = validated_data.pop("node", None)
        instance = super().update(instance, validated_data)
        if instance.is_system_template:
            raise serializers.ValidationError(
                "System templates cannot be updated.")
        instance.fields.all().delete()
        self._create_fields(instance, fields)
        self._create_upload(instance, node)
        self._create_node_template(instance, node)
        return instance

    @staticmethod
    def get_latest_upload(instance):
        """Get the latest upload for the template.

        This method returns the latest upload file for the template.

        This method fetches the uploads associated with the template and
        serializes the first upload using the DataSheetUploadSerializer. The
        'is_used' and 'id' fields are included in the serialization.
        """
        uploads = instance.uploads.all()
        if uploads.exists():
            return DataSheetUploadSerializer(
                uploads.first(),
                fields=("id", "is_used")).data
        return {}

    def _create_fields(self, template, fields):
        """Create fields for the template.

        This method creates DataSheetTemplateField instances for the
        given template and field values. The field objects are bulk
        created using the 'bulk_create' method for better performance.
        """
        field_objects = []
        self._validate_mandatory_fields(template, fields)
        self._validate_farmer_reference(fields)

        for field_values in fields:
            field_objects.append(
                DataSheetTemplateField(template=template, **field_values)
            )
        if field_objects:
            DataSheetTemplateField.objects.bulk_create(field_objects)

    @staticmethod
    def _create_node_template(template, node):
        """Link the node to the template.

        This method links the template to a node if available. The node
        is retrieved from the serializer's context using the 'view'
        attribute.
        """
        if node:
            NodeDataSheetTemplates.objects.get_or_create(
                node=node, template=template)

    def _create_upload(self, instance, node):
        """Create an upload for the template."""
        if (instance.is_active and
                not instance.uploads.filter(node=node).exists()):
            data = {
                "template": instance.idencode,
                "file": instance.file._get_file(),  # noqa
                "file_name": instance.file.name,
                "product": (instance.product.idencode
                            if instance.product else None),
                "supply_chain": (instance.supply_chain.idencode
                            if instance.supply_chain else None),
                "node": node.idencode,
                "unit": instance.unit,
                "currency": instance.currency}
            upload_serializer = DataSheetUploadSerializer(data=data,
                                                          context=self.context)
            upload_serializer.is_valid(raise_exception=True)
            upload_serializer.save()

    @staticmethod
    def _validate_farmer_reference(fields):
        """Validate the farmer reference fields. """
        if not fields:
            return fields
        farmer_upload_schema = FarmerUploadSchema
        name_list = list(map(lambda x: x.get("name"), fields))
        farmer_id_check = ("fair_id" in name_list, "identification_no" in
                           name_list)
        farmer_name_check = map(
            lambda key: key in name_list,
            farmer_upload_schema.get_mandatory_fields().keys()
        )
        if not any(farmer_id_check) and not all(farmer_name_check):
            raise serializers.ValidationError(
                "Farmer identification or details fields are required for "
                "saving template fields."
            )

    @staticmethod
    def _validate_mandatory_fields(template, fields):
        """Validate the mandatory fields."""
        if not fields:
            return fields
        name_list = list(map(lambda x: x.get("name"), fields))
        schema = (TransactionUploadSchema
                  if template.type == constants.TEMPLATE_TYPE_TXN
                  else FarmerUploadSchema)
        mandatory_fields = schema.get_mandatory_fields().keys()
        if not set(mandatory_fields).issubset(set(name_list)):
            raise serializers.ValidationError(
                "Mandatory fields are required for saving template fields."
            )
