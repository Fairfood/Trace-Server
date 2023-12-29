"""Serializers for transaction related APIs."""
from common import library as comm_lib
from common.drf_custom import fields as custom_fields
from common.drf_custom.serializers import IdencodeModelSerializer
from common.exceptions import BadRequest
from openpyxl import load_workbook
from rest_framework import serializers
from v2.accounts.models import FairfoodUser
from v2.products.models import Product
from v2.products.serializers import product as prods_serializers
from v2.supply_chains import constants as sc_constants
from v2.supply_chains.models import BulkExcelUploads
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Node
from v2.supply_chains.models import SupplyChain
from v2.transactions import constants as txn_constants
from v2.transactions.bulk_upload.transaction_sheet import (
    FarmerWithTransactionExcel,
)
from v2.transactions.models import Transaction
from v2.transactions.models import TransactionAttachment


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for common transaction fields."""

    id = custom_fields.IdencodeField(read_only=True)
    # date = serializers.DateField(format="%d %B %Y")
    date = serializers.DateTimeField(required=False)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "number",
            "date",
            "blockchain_address",
            "status",
            "transaction_type",
        )


class DestinationBatchSerializer(serializers.Serializer):
    """Serializer for validating destination products in a transaction."""

    product = custom_fields.IdencodeField(
        related_model=Product, serializer=prods_serializers.ProductSerializer
    )
    quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3
    )
    unit = serializers.IntegerField()


class BulkQuantitySerializer(serializers.Serializer):
    """Serializer to calculate quantity of product received from each
    farmer."""

    node = serializers.CharField()
    quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3
    )


class TransactionTemplateSerializer(serializers.ModelSerializer):
    """Serializer to validate uploaded excel."""

    id = custom_fields.IdencodeField(read_only=True)
    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True
    )
    node = custom_fields.KWArgsObjectField(related_model=Node, write_only=True)
    supply_chain = custom_fields.IdencodeField(
        related_model=SupplyChain, write_only=True, required=False
    )
    file = serializers.FileField(write_only=True)

    class Meta:
        model = BulkExcelUploads
        fields = ("id", "user", "node", "supply_chain", "file")
        extra_kwargs = {"file": {"required": True}}

    def create_bulk_upload_file(self, validated_data, data):
        """Function for create bulk excel upload file."""
        validated_data["data"] = data
        validated_data["creator"] = validated_data.pop("user")
        validated_data["updater"] = validated_data["creator"]
        validated_data[
            "type"
        ] = sc_constants.BULK_UPLOAD_TYPE_CONNECTION_TRANSACTION
        validated_data["farmers_to_add"] = data["farmers_to_add"]
        validated_data["farmers_to_update"] = data["farmers_to_update"]
        validated_data["transactions_to_add"] = data["transactions_to_add"]

        bulk_file = super(TransactionTemplateSerializer, self).create(
            validated_data
        )
        return bulk_file

    def check_fair_id(self, encoded_id):
        """Function for verify fair_id in excel is valid or not."""
        is_farmer = True
        farmer_encoded_id = encoded_id
        if farmer_encoded_id:
            farmer_id = comm_lib._decode(farmer_encoded_id)
            farmer_object = Farmer.objects.filter(id=farmer_id)
            if not farmer_object:
                is_farmer = False
        return is_farmer

    def validate_excel(self, fields_list):
        """To perform function validate_excel."""
        is_farmer = False
        for row_data in fields_list:
            if "fields" in row_data:
                for field in row_data["fields"]:
                    if field["key"] == "id":
                        is_farmer = self.check_fair_id(field["value"])
                    if field["key"] == "product":
                        product = field["value"]
                    if field["key"] == "product_id":
                        product_id = field["value"]
                if not product or not product_id or not is_farmer:
                    txt = "FairID or Product"
                    response = {
                        "valid": False,
                        "message": txn_constants.FILE_CORRUPTED_MSG % txt,
                        "status": txn_constants.FILE_CORRUPTED_STATUS,
                    }
                    return response
        return {"valid": True}

    def create(self, validated_data):
        """Function to load bulk transaction excel and validate the data."""
        res = BulkExcelUploads.is_file_exists(
            validated_data["file"], validated_data["node"]
        )
        validated_data["file_hash"] = res.pop("file_hash", None)
        if res["valid"]:
            res["status"] = txn_constants.DUPLICATE_TXN
            return res
        try:
            wb = load_workbook(validated_data["file"], data_only=True)
        except Exception:
            raise BadRequest("Could not read this file. Format incorrect")
        try:
            sc_id = comm_lib._decode(
                self.context["request"].query_params["supply_chain"]
            )
            supply_chain = SupplyChain.objects.get(id=sc_id)
        except Exception:
            supply_chain = None
        excel = FarmerWithTransactionExcel(workbook=wb)
        data = excel.validate(validated_data["node"], supply_chain)
        fields_list = data["excel_data"]["row_data"]
        response = self.validate_excel(fields_list)
        if not response["valid"]:
            return response
        bulk_file = self.create_bulk_upload_file(validated_data, data)
        data["excel_data"]["farmers"] = data["excel_data"].pop("row_data")
        data["file"] = bulk_file.idencode
        return data

    def to_representation(self, data):
        """To perform function to_representation."""
        return data


class TransactionAttachmentSerializer(IdencodeModelSerializer):
    """Serializer class for TransactionAttachment model.

    This serializer serializes TransactionAttachment instances,
    providing the necessary fields and customization options.
    """

    node_name = serializers.CharField(source="node.full_name", read_only=True)

    class Meta:
        fields = "__all__"
        model = TransactionAttachment
