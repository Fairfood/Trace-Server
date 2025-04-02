"""Serializers for intenal transactions."""
from collections import OrderedDict
from common import library as common_lib
from common.drf_custom import fields as custom_fields
from django.conf import settings
from django.db import transaction as django_transaction
from rest_framework import serializers
from v2.claims.serializers import product_claims
from v2.products import constants as prod_constants
from v2.products.models import Batch
from v2.products.serializers import batch as batch_serializers
from v2.products.serializers import product as prods_serializers
from v2.transactions import constants as trans_constants
from v2.transactions.models import InternalTransaction
from v2.transactions.models import SourceBatch
from v2.transactions.tasks import transaction_follow_up
from django.db.models import Q

from ...accounts.serializers.user import UserListSerializer
from ...dashboard.models import CITheme
from .other import DestinationBatchSerializer


class InternalTransactionSerializer(serializers.ModelSerializer):
    """Serializer to create internal transactions."""

    # Write only fields for creation
    user = custom_fields.KWArgsObjectField(write_only=True)
    node = custom_fields.KWArgsObjectField(write_only=True)
    type = serializers.IntegerField(required=False)
    batch_type = serializers.IntegerField(required=False)
    select_all_batches = serializers.BooleanField(default=False, 
                                                  write_only=True)
    source_batches = batch_serializers.SourceBatchSerializer(
        write_only=True, many=True, required=False
    )
    destination_batches = DestinationBatchSerializer(
        write_only=True, many=True, required=False
    )

    # Read only fields for output
    id = custom_fields.IdencodeField(read_only=True)
    number = serializers.IntegerField(read_only=True)
    source_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True
    )
    destination_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True, required=False
    )
    blockchain_address = serializers.CharField(read_only=True)
    source_products = serializers.SerializerMethodField(
        "get_source_products", read_only=True
    )
    destination_products = serializers.SerializerMethodField(
        "get_destination_products", read_only=True
    )
    transaction_type = serializers.IntegerField(read_only=True)
    created_on = custom_fields.UnixTimeField(required=False)
    logged_time = serializers.DateTimeField(
        source="created_on", read_only=True
    )
    claims = custom_fields.ManyToManyIdencodeField(
        serializer=product_claims.BatchClaimSerializer,
        source="get_claims",
        read_only=True,
    )
    client_type = serializers.IntegerField(default=trans_constants.CLIENT_WEB)
    invoice = serializers.FileField(required=False)

    class Meta:
        model = InternalTransaction
        fields = (
            "id",
            "external_id",
            "user",
            "node",
            "type",
            "mode",
            "date",
            "select_all_batches",
            "source_batches",
            "destination_batches",
            "number",
            "explorer_url",
            "source_quantity",
            "destination_quantity",
            "source_products",
            "destination_products",
            "blockchain_address",
            "batch_type",
            "transaction_type",
            "logged_time",
            "comment",
            "claims",
            "client_type",
            "invoice",
            "created_on",
            "archived"
        )

    def get_source_products(self, instance):
        """Product data of source batches."""
        data = []
        for source_batch in instance.source_batch_objects.all():
            product_data = prods_serializers.ProductSerializer(
                source_batch.batch.product
            ).data
            product_data["id"] = source_batch.batch.idencode
            product_data["quantity"] = source_batch.quantity
            product_data["number"] = source_batch.batch.number
            product_data["unit"] = source_batch.batch.unit
            product_data[
                "total_farmers"
            ] = source_batch.batch.batch_farmers.count()
            data.append(product_data)
        return data

    def get_destination_products(self, instance):
        """Product data of destination batches."""
        data = []
        for result_batch in instance.result_batches.all():
            product_data = prods_serializers.ProductSerializer(
                result_batch.product
            ).data
            product_data["id"] = result_batch.idencode
            product_data["quantity"] = result_batch.initial_quantity
            product_data["number"] = result_batch.number
            product_data["unit"] = result_batch.unit
            product_data["total_farmers"] = result_batch.batch_farmers.count()
            data.append(product_data)
        return data

    def validate(self, attrs):
        """For loss transaction destination batch is not required, but for
        every other transactions, it is required."""
        if "type" in attrs.keys():
            if attrs["type"] != trans_constants.INTERNAL_TRANS_TYPE_LOSS:
                if "destination_batches" not in attrs:
                    raise serializers.ValidationError(
                        "destination_batches is required."
                    )
        return attrs

    def prepare_batches(self, validated_data):
        """If batches of multiple products are used for an internal
        transaction, some internal transaction will be created by the system to
        handle this.This will be different for different type of internal
        transactions.

        If product A, B, C are merged together as D,
            A will be converted to D
            B will be converted to D
            C will be converted to D
            Then the 3 output batches will be merged together

        If it is a processing transaction, it can have source batches
        of different types and different destination batches,
         so no system transaction will be created.
        """
        select_all_batches = validated_data.pop("select_all_batches", False)
        validated_data['source_batches'] = validated_data.get('source_batches', 
                                                              [])
        if select_all_batches:
            self._get_only_batches_to_batches(validated_data["source_batches"])

        if not validated_data["source_batches"]:
            raise serializers.ValidationError(
                "source_batches is required."
            )

        if validated_data["type"] != trans_constants.INTERNAL_TRANS_TYPE_MERGE:
            return validated_data
        
        

        
        product_ids = [
            i["batch"].product.id for i in validated_data["source_batches"]
        ]
        if len(set(product_ids)) == 1:
            return validated_data
        if len(validated_data["destination_batches"]) == 1:
            destination_batch = validated_data["destination_batches"][0]
        else:
            raise serializers.ValidationError(
                "Merging transaction can have only one destination batch"
            )
        new_source_batch = []
        for batch in validated_data["source_batches"]:
            if batch["batch"].product != destination_batch["product"]:
                int_tran_data = {
                    "type": trans_constants.INTERNAL_TRANS_TYPE_PROCESSING,
                    "mode": trans_constants.TRANSACTION_MODE_SYSTEM,
                    "comment": validated_data.get("comment", ""),
                    "source_batches": [
                        {
                            "batch": batch["batch"].idencode,
                            "quantity": batch["quantity"],
                        }
                    ],
                    "destination_batches": [
                        {
                            "product": destination_batch["product"].idencode,
                            "quantity": batch["quantity"],
                            "unit": batch["batch"].unit,
                        }
                    ],
                    "batch_type": prod_constants.BATCH_TYPE_INTERMEDIATE,
                }
                if "date" in validated_data:
                    int_tran_data["date"] = validated_data["date"]
                int_tran_serializer = InternalTransactionSerializer(
                    data=int_tran_data, context=self.context
                )
                if not int_tran_serializer.is_valid():
                    raise serializers.ValidationError(
                        int_tran_serializer.errors
                    )
                int_trans = int_tran_serializer.save()
                result_batch = int_trans.result_batches.first()
                new_source_batch.append(
                    {
                        "batch": result_batch,
                        "quantity": result_batch.initial_quantity,
                    }
                )
            else:
                new_source_batch.append(batch)
        validated_data["source_batches"] = new_source_batch
        return validated_data
    
    def _get_only_batches_to_batches(self, only_changed_batches):
        """Retrieves batches associated with a specific node that are not
        already present in the 'only_changed_batches' list.

        This method is responsible for finding batches associated with a
        specific node that are not present in the
        'only_changed_batches' list. The 'only_changed_batches' list should
        contain dictionaries with 'batch' and 'quantity' keys.

        Args:
            only_changed_batches (list): A list of dictionaries, each
            containing 'batch' and 'quantity' keys.
        """
        try:
            node = self.context.get("view").kwargs.get("node")
        except KeyError:
            node = self.context.get("node")

        if node:
            batch_ids = [
                batch_data["batch"].pk for batch_data in only_changed_batches
            ]
            batch_qs = Batch.objects.filter(
                Q(node_id=node.id, current_quantity__gt=0)
                & ~Q(pk__in=batch_ids)
            )
            batch_qs = batch_qs.filter(archived=False)
            batch_qs = batch_qs.only("id", "current_quantity")
            only_changed_batches.extend(
                [
                    OrderedDict(
                        {"batch": batch, "quantity": batch.current_quantity}
                    )
                    for batch in batch_qs
                ]
            )

    @django_transaction.atomic
    def create(self, validated_data):
        """To perform function create."""
        validated_data["creator"] = validated_data["user"]
        validated_data["updater"] = validated_data["user"]
        validated_data["node_wallet"] = validated_data[
            "node"
        ].setup_blockchain_account()
        validated_data = self.prepare_batches(validated_data)
        source_batches = validated_data.pop("source_batches")
        if "created_on" in validated_data.keys():
            validated_data["date"] = validated_data["created_on"]
        batch_type = validated_data.pop(
            "batch_type", prod_constants.BATCH_TYPE_SOLID
        )
        destination_batches = validated_data.pop("destination_batches", None)
        common_lib._pop_out_from_dictionary(validated_data, ["user"])
        transaction = InternalTransaction.objects.create(**validated_data)
        batches = []
        for batch_data in source_batches:
            batch = batch_data["batch"]
            batches.append(batch)
            qty = batch_data["quantity"]
            if batch.current_quantity < qty:
                raise serializers.ValidationError(
                    "Not enough quantity in Batch"
                )
            batch.current_quantity -= qty
            batch.save()
            SourceBatch.objects.create(
                transaction=transaction,
                batch=batch,
                quantity=qty,
                creator=validated_data["creator"],
                updater=validated_data["updater"],
            )
            if batch.source_transaction:
                transaction.add_parent(batch.source_transaction)
        if transaction.type != trans_constants.INTERNAL_TRANS_TYPE_LOSS:
            for product_data in destination_batches:
                result_batch = Batch.objects.create(
                    product=product_data["product"],
                    node=validated_data["node"],
                    initial_quantity=product_data["quantity"],
                    current_quantity=product_data["quantity"],
                    unit=product_data["unit"],
                    name="Created by %s" % transaction.get_type_display(),
                    creator=validated_data["creator"],
                    updater=validated_data["updater"],
                    source_transaction=transaction,
                    type=batch_type,
                    note=validated_data.get("comment", ""),
                )
                for b in batches:
                    result_batch.parents.add(b)
                    result_batch.update_batch_farmers()
                if transaction.mode == trans_constants.TRANSACTION_MODE_SYSTEM:
                    result_batch.inherit_claims()

        django_transaction.on_commit(
            lambda: transaction_follow_up.delay(transaction.id)
        )
        return transaction

    def to_representation(self, instance):
        """To perform function to_representation."""
        data = super().to_representation(instance)
        data["consumer_interface_url"] = self._get_consumer_interface_url(
            instance.node
        )
        return data

    @staticmethod
    def _get_consumer_interface_url(node):
        """To perform function _get_consumer_interface_url."""
        theme = CITheme.objects.filter(node=node).first()
        if not theme:
            theme = CITheme.objects.filter(is_public=True).first()
        if theme.version != "0" and settings.CONSUMER_INTERFACE_V2_URL:
            return settings.CONSUMER_INTERFACE_V2_URL
        return ""


class InternalTransactionListSerializer(serializers.ModelSerializer):
    """Serializer for details in the list page of internal transactions."""

    id = custom_fields.IdencodeField(read_only=True)
    creator = custom_fields.IdencodeField(
        read_only=True, serializer=UserListSerializer
    )
    number = serializers.IntegerField(read_only=True)
    source_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True
    )
    destination_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True, required=False
    )
    blockchain_address = serializers.CharField(read_only=True)
    source_batches = serializers.SerializerMethodField(
        "get_source_products", read_only=True
    )
    destination_batches = serializers.SerializerMethodField(
        "get_destination_products", read_only=True
    )
    # date = serializers.DateField(
    #     format="%d %b %Y", input_formats=["%Y-%m-%d"],
    #     required=False)
    date = serializers.DateTimeField(required=False)
    logged_time = serializers.DateTimeField(
        source="created_on", read_only=True
    )

    class Meta:
        model = InternalTransaction
        fields = (
            "id",
            "date",
            "type",
            "mode",
            "number",
            "source_quantity",
            "destination_quantity",
            "source_batches",
            "destination_batches",
            "blockchain_address",
            "logged_time",
            "creator",
            "archived"
        )

    def get_source_products(self, instance):
        """To perform function get_source_products."""
        data = []
        for source_batch in instance.source_batch_objects.all():
            if (
                source_batch.batch.type
                == prod_constants.BATCH_TYPE_INTERMEDIATE
            ):
                source_batch = source_batch.batch.get_source_batches()
            product_data = prods_serializers.ProductSerializer(
                source_batch.batch.product
            ).data
            product_data["id"] = source_batch.batch.idencode
            product_data["product_id"] = source_batch.batch.product.idencode
            product_data["quantity"] = source_batch.quantity
            product_data["number"] = source_batch.batch.number
            product_data["unit"] = source_batch.batch.unit
            product_data[
                "total_farmers"
            ] = source_batch.batch.batch_farmers.count()
            data.append(product_data)
        return data

    def get_destination_products(self, instance):
        """To perform function get_destination_products."""
        data = []
        for result_batch in instance.result_batches.all():
            product_data = prods_serializers.ProductSerializer(
                result_batch.product
            ).data
            product_data["id"] = result_batch.idencode
            product_data["product_id"] = result_batch.product.idencode
            product_data["quantity"] = result_batch.initial_quantity
            product_data["number"] = result_batch.number
            product_data["unit"] = result_batch.unit
            product_data["total_farmers"] = result_batch.batch_farmers.count()
            data.append(product_data)
        return data
