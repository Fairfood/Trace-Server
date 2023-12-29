"""Serializers for bulk template."""
import os

import openpyxl as xl
import pandas as pd
from common import library as comm_lib
from common.drf_custom import fields as custom_fields
from common.drf_custom import serializers as custom_seri
from common.exceptions import BadRequest
from django.conf import settings
from django.db import transaction as django_transaction
from django.utils import timezone
from django.utils.timezone import datetime
from rest_framework import serializers
from v2.accounts.models import FairfoodUser
from v2.bulk_templates import constants as temp_const
from v2.bulk_templates import models as temp_models
from v2.bulk_templates.dynamic_bulk_upload.txn_sheet import (
    DynamicExcelProcessor,
)
from v2.products.models import Product
from v2.supply_chains import constants as sc_constants
from v2.supply_chains.models import BulkExcelUploads
from v2.supply_chains.models import Node
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.tasks import upload_bulk_transaction
from v2.transactions import constants as txn_constants


class TemplateTypeFieldSerializer(custom_seri.IdencodeModelSerializer):
    """Serializer for Template Type Field."""

    class Meta:
        """Meta Data."""

        model = temp_models.TemplateTypeField
        fields = "__all__"


class TemplateFieldSerializer(custom_seri.IdencodeModelSerializer):
    """serializer for create Template Field."""

    class Meta:
        model = temp_models.TemplateField
        fields = ("id", "column_pos", "field")

    def to_representation(self, instance):
        """How to represent data."""
        data = super(TemplateFieldSerializer, self).to_representation(instance)
        data["field"] = {
            "id": instance.field.idencode,
            "column_pos": data.pop("column_pos", 0),
            "name": instance.field.name,
            "key": instance.field.key,
            "required": instance.field.required,
            "meta": instance.field.meta,
        }
        return data


class DynamicBulkUploadSerializer(custom_seri.IdencodeModelSerializer):
    """serializer for create bulk uploads."""

    creator = custom_fields.IdencodeField(
        related_model=FairfoodUser, required=False
    )
    updater = custom_fields.IdencodeField(
        related_model=FairfoodUser, required=False
    )
    node = custom_fields.IdencodeField(related_model=Node, required=False)
    template = custom_fields.IdencodeField(
        related_model=temp_models.Template, required=False
    )

    class Meta:
        model = temp_models.DynamicBulkUpload
        fields = (
            "id",
            "creator",
            "updater",
            "template",
            "node",
            "supply_chain",
            "file",
            "file_hash",
        )
        extra_kwargs = {"file": {"required": True}}

    def create(self, validated_data):
        """Function to load bulk transaction excel and validate the data."""
        validated_data["type"] = sc_constants.BULK_UPLOAD_TYPE_TRANSACTION_ONLY
        bulk_file = super(DynamicBulkUploadSerializer, self).create(
            validated_data
        )
        return bulk_file


class NodeTemplateSerializer(custom_seri.IdencodeModelSerializer):
    """Serializer for node template."""

    node = custom_fields.KWArgsObjectField(related_model=Node, write_only=True)
    product_detail = serializers.SerializerMethodField(
        "get_product_detail", default=None
    )
    template = custom_fields.IdencodeField(
        related_model=temp_models.Template, required=False
    )
    product = custom_fields.IdencodeField(
        related_model=Product, required=False
    )
    """Serializer for NodeTemplate."""

    class Meta:
        """Meta Data."""

        model = temp_models.NodeTemplate
        fields = (
            "node",
            "product",
            "template",
            "unit",
            "currency",
            "product_detail",
        )

    def get_product_detail(self, instance):
        """returns product details."""
        if not instance.product:
            return None
        return {
            "id": instance.product.idencode,
            "name": instance.product.name,
            "supply_chain": instance.product.supply_chain.idencode,
        }


class TemplateSerializer(custom_seri.IdencodeModelSerializer):
    """Serializer to create node template."""

    node_temp = NodeTemplateSerializer(
        allow_null=True, many=True, source="node_templates", required=False
    )
    temp_fields = TemplateFieldSerializer(
        allow_null=True, many=True, source="template_fields", required=False
    )
    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True
    )
    node = custom_fields.KWArgsObjectField(related_model=Node, write_only=True)
    bulk_file = custom_fields.IdencodeField(required=False)
    product = custom_fields.IdencodeField(
        related_model=Product, required=False
    )
    file = serializers.FileField(required=False)
    excel_data = serializers.ListField(required=False, allow_empty=False)
    type_fields = serializers.ListField(required=False)
    is_saved = serializers.BooleanField(required=False)
    name = serializers.CharField(required=False, allow_blank=True)
    currency = serializers.CharField(required=False)
    unit = serializers.IntegerField(required=False)
    is_deleted = serializers.BooleanField(required=False)
    creator = serializers.SerializerMethodField("get_creator")
    updater = serializers.SerializerMethodField("get_updater")
    download = serializers.BooleanField(read_only=True, default=False)
    bulk_file_id = serializers.SerializerMethodField("get_bulk_file_id")

    class Meta:
        model = temp_models.Template
        exclude = ("nodes",)

    def get_bulk_file_id(self, instance):
        """Returns bulk file id."""
        try:
            bulk_id = instance.bulk_template.get(
                node=self.context["view"].kwargs["node"]
            ).idencode
            return bulk_id
        except Exception:
            return None

    def get_creator(self, instance):
        """Function for get creator details."""
        return {"id": instance.creator.idencode, "name": instance.creator.name}

    def get_updater(self, instance):
        """Function for get updater details."""
        return {"id": instance.updater.idencode, "name": instance.updater.name}

    def validate(self, attrs):
        """Function for check duplicate of file.

        and generate a new attribute file hash.
        """
        if "file" in attrs:
            file_check = BulkExcelUploads.is_file_exists(
                attrs["file"], attrs["node"]
            )
            attrs["file_hash"] = file_check["file_hash"]
            if file_check["valid"]:
                raise serializers.ValidationError(file_check["message"])
        if "name" in attrs:
            attrs["name"] = attrs["name"].capitalize()
        return attrs

    def validate_excel_format(self, file):
        """Function for validate excel format."""
        try:
            pd.read_excel(file)
        except Exception as e:
            raise BadRequest("Could not read this file. Format incorrect", e)
        return True

    def create_bulk_upload_file(self, template, file_hash):
        """Function for create bulk upload file."""
        data = {
            "file": template.file,
            "template": template,
            "node": template.nodes.all()[0],
            "file_hash": file_hash,
            "creator": template.creator,
            "updater": template.updater,
        }
        bulk_serializer = DynamicBulkUploadSerializer(data=data)
        if not bulk_serializer.is_valid():
            raise BadRequest(bulk_serializer.errors)
        bulk_file = bulk_serializer.save()
        return bulk_file

    def create(self, validated_data):
        """Function to save bulk transaction excel and read some row datas and
        return in response.

        check file is duplicate or not.
        """
        self.validate_excel_format(validated_data["file"])
        file_hash = validated_data.pop("file_hash", None)
        data = {}
        data["creator"] = validated_data.pop("user", None)
        data["updater"] = data["creator"]
        data["file"] = validated_data.pop("file", None)
        data["name"] = temp_const.CUSTOM_TEMP_NAME
        if "product" in validated_data:
            data["name"] = (
                temp_const.CUSTOM_TEMP_NAME
                + " "
                + str(validated_data["product"].name)
            ).capitalize()
        template = super(TemplateSerializer, self).create(data)
        template.save()
        validated_data["template"] = template
        node_temp_serializer = NodeTemplateSerializer(
            data=validated_data, context=self.context
        )
        if not node_temp_serializer.is_valid():
            raise serializers.ValidationError(node_temp_serializer.errors)
        node_temp_serializer.save()
        bulk_file_obj = self.create_bulk_upload_file(template, file_hash)
        # data = template.set_meta_data
        processor = DynamicExcelProcessor(bulk_file_obj)
        template.excel_data = processor.get_preview()
        template.bulk_file = bulk_file_obj.id
        # self.clear_excel_data(bulk_file, data['data_row'], template)
        return template

    def clear_excel_data(self, bulk_file, data_row, template):
        """Function for clear data from excel sheet.

        save a temporary file locally and open excel. then delete data
        rows except heading rows.
        """
        file_path = bulk_file.save_temp_excel()
        wb = xl.load_workbook(file_path)
        ws = wb.active
        ws.delete_rows(data_row + 1, ws.max_row)
        dest_filename = bulk_file.filename
        path = comm_lib._get_file_path(template, dest_filename)
        path = settings.MEDIA_URL + path
        wb.save(os.path.join(path))
        return True

    def _update_or_create_template_field(self, data):
        """To perform function _update_or_create_template_field."""
        type_fields = data.pop("type_fields", None)
        if not type_fields:
            return False
        for type_field in type_fields:
            try:
                data["column_pos"] = comm_lib.convert_letter_to_number(
                    type_field.pop("column_pos", None)
                )
                data["field"] = temp_models.TemplateTypeField.objects.get(
                    id=comm_lib._decode(type_field.pop("id", None))
                )
            except Exception:
                raise ValueError("Invalid Field ID")

            meta = temp_models.TemplateField._meta
            extra_keys = list(
                set([field.name for field in meta.get_fields()]) ^ set([*data])
            )
            comm_lib._pop_out_from_dictionary(data, extra_keys)

            temp_field = temp_models.TemplateField.objects.filter(
                template=data["template"], field=data["field"]
            )
            if temp_field:
                temp_field.update(**data)
            else:
                temp_models.TemplateField.objects.create(**data)
        return True

    def update(self, instance, validated_data):
        """Function to create template field.

        update template objects.
        """
        validated_data["creator"] = validated_data.pop("user")
        validated_data["updater"] = validated_data["creator"]
        visibility = validated_data.pop("is_saved", None)
        if visibility:
            validated_data[
                "visibility"
            ] = temp_const.TEMPLATE_VISIBILITY_PRIVATE
        if "name" in validated_data:
            if not validated_data["name"]:
                validated_data["name"] = instance.name

        type_fields = validated_data.pop("type_fields", None)
        template = super(TemplateSerializer, self).update(
            instance, validated_data
        )
        validated_data["template"] = template
        validated_data["type_fields"] = type_fields
        self._update_or_create_template_field(validated_data)
        return template


class VerifyTemplateSerializer(custom_seri.IdencodeModelSerializer):
    """Serializer to validate template excel."""

    product = custom_fields.IdencodeField(
        related_model=Product, required=False
    )
    bulk_file = custom_fields.IdencodeField(required=False)
    supply_chain = custom_fields.IdencodeField(
        related_model=SupplyChain, required=False
    )
    node = custom_fields.KWArgsObjectField(related_model=Node, write_only=True)
    file = serializers.FileField(write_only=True)
    name = serializers.CharField(required=False)
    currency = serializers.CharField(required=False)
    unit = serializers.IntegerField(required=False)
    temp_id = serializers.CharField(required=False)

    class Meta:
        model = temp_models.Template
        fields = (
            "id",
            "name",
            "product",
            "unit",
            "currency",
            "file",
            "bulk_file",
            "node",
            "supply_chain",
            "temp_id",
        )

    def validate(self, attrs):
        """Validate data."""
        file_check = BulkExcelUploads.is_file_exists(
            attrs["file"], attrs["node"]
        )
        if file_check["valid"]:
            raise serializers.ValidationError(file_check["message"])
        return attrs

    def validate_excel_format(self, file):
        """Function for validate excel format."""
        try:
            pd.read_excel(file)
        except Exception:
            raise BadRequest("Could not read this file. Format incorrect")
        return True

    def _set_response(self, data, bulk_temp, validated_data):
        """To perform function _set_response."""
        data["bulk_file"] = bulk_temp.idencode
        data["node"] = bulk_temp.template.nodes.all()[0].idencode
        data["unit"] = validated_data["unit"]
        data["currency"] = validated_data["currency"]
        return True

    def _update_file(self, validated_data):
        """To perform function _update_file."""
        bulk_temp = temp_models.DynamicBulkUpload.objects.get(
            template_id=comm_lib._decode(validated_data["temp_id"])
        )
        file = validated_data.pop("file", None)
        bulk_temp.file = file
        bulk_temp.save()
        # bulk_temp.template.file = bulk_temp.file
        # bulk_temp.template.save()
        return bulk_temp

    def _update_node_template(self, bulk_temp, validated_data):
        """To perform function _update_node_template."""
        node_temp = bulk_temp.template.node_templates.get(
            node=validated_data["node"]
        )
        node_temp.product = validated_data["product"]
        node_temp.unit = validated_data["unit"]
        node_temp.currency = validated_data["currency"]
        node_temp.save()
        return True

    def create(self, validated_data):
        """Function to load bulk transaction excel and validate the data."""
        self.validate_excel_format(validated_data["file"])
        bulk_temp = self._update_file(validated_data)
        self._update_node_template(bulk_temp, validated_data)
        excel = DynamicExcelProcessor(bulk_temp)
        data = excel.validate(
            validated_data["product"], validated_data["supply_chain"]
        )
        bulk_temp.data = data
        bulk_temp.save()
        self._set_response(data, bulk_temp, validated_data)
        return data

    def to_representation(self, data):
        """How to represent data."""
        return data


class TxnBulkSerializer(custom_seri.IdencodeModelSerializer):
    """Serializer for Bulk transaction."""

    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True
    )
    row_data = serializers.ListField(allow_empty=False, required=False)
    product = serializers.CharField(required=False)
    currency = serializers.CharField(required=False)
    node = serializers.CharField(required=False)
    unit = serializers.IntegerField(required=False)

    class Meta:
        model = temp_models.DynamicBulkUpload
        fields = (
            "user",
            "row_data",
            "product",
            "file_hash",
            "currency",
            "unit",
            "node",
        )

    def update(self, instance, validated_data):
        """To update bulk upload objects."""
        file_hash = comm_lib._hash_file(instance.file)
        user = validated_data.pop("user", None)
        bulk_data = {
            "data": validated_data,
            "updater": user,
            "used": True,
            "file_hash": file_hash,
        }
        bulk_file = super(TxnBulkSerializer, self).update(
            instance=instance, validated_data=bulk_data
        )
        django_transaction.on_commit(
            lambda: upload_bulk_transaction.delay(bulk_file.id)
        )
        return bulk_file


class TxnBulkSerializerAsync(serializers.Serializer):
    """Serializer for Bulk creation of transaction."""

    row_data = serializers.ListField(allow_empty=False)
    product = serializers.CharField(required=False)
    currency = serializers.CharField(required=False)
    node = serializers.CharField(required=False)
    unit = serializers.IntegerField(required=False)

    def create(self, validated_data):
        """function to load exel row data and create external transaction."""
        for txn_data in validated_data["row_data"]:
            if "date" in txn_data:
                time = timezone.now().time()
                date = txn_data["date"] + "-" + str(time)
                txn_data["date"] = datetime.strptime(
                    date, "%Y-%m-%d-%H:%M:%S.%f"
                )
            from v2.transactions.serializers.external import (
                ExternalTransactionSerializer,
            )

            txn_data["type"] = txn_constants.EXTERNAL_TRANS_TYPE_INCOMING
            # through excel always create txn object, if txn is
            # also duplicate. so pass force_create key as true.
            txn_data["force_create"] = True
            txn_data["currency"] = validated_data["currency"]
            txn_data["unit"] = validated_data["unit"]
            txn_data["product"] = validated_data["product"]
            transaction_serializer = ExternalTransactionSerializer(
                data=txn_data, context=self.context
            )
            if not transaction_serializer.is_valid():
                raise serializers.ValidationError(
                    transaction_serializer.errors
                )
            transaction_serializer.save()
        return validated_data


class ValidateTemplateNameSerializer(serializers.Serializer):
    """Serializer to check the username availability."""

    name = serializers.CharField()
    node = serializers.CharField()

    def to_representation(self, obj):
        """Overriding the value returned when returning the serializer."""
        data = {}
        template = temp_models.Template.objects.filter(
            name=obj["name"].capitalize(),
            nodes=comm_lib._decode(obj["node"]),
            is_deleted=False,
        )
        if template.exists():
            data["available"] = False
            data["valid"] = False
            data["message"] = "Template name already taken"
            data["id"] = template[0].idencode
        else:
            data["available"] = True
            data["valid"] = True
            data["message"] = "Template name available"
            data["id"] = None
        return data
