"""Serializer for carbon transactions"""

from collections import OrderedDict
from django.conf import settings
from django.db import transaction as django_transaction
from django.db.models import Q
from rest_framework import serializers
from common import library as common_lib
from common.drf_custom import fields as custom_fields
from common.exceptions import BadRequest
from v2.claims.serializers import product_claims
from v2.dashboard.models import CITheme
from v2.products import constants as prod_constants
from v2.products.models import Batch
from v2.products.models import Product
from v2.products.serializers import batch as batch_serializers
from v2.products.serializers import product as prods_serializers
from v2.projects.models import NodeCard
from v2.projects.serializers.project import NodeCardSerializer
from v2.supply_chains.models import Node
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.supply_chains.serializers.public import NodeWalletSerializer
from v2.transactions import constants as trans_constants
from v2.transactions.models import ExternalTransaction, InternalTransaction
from v2.transactions.models import SourceBatch
from v2.transactions.serializers.internal import InternalTransactionSerializer
from v2.transactions.serializers.external import IssuedPremiumSerializer
from v2.transactions.serializers.other import DestinationBatchSerializer
from v2.transactions.tasks import transaction_follow_up
from v2.transactions.constants import (
    TRANSACTION_TYPE_EXTERNAL, INTERNAL_TRANS_TYPE_LOSS, 
    CARBON_TRANSACTION_TYPE_MAP
)
from v2.transparency_request import constants as trr_constants
from v2.transparency_request.models import StockRequest
from v2.transparency_request.serializers.public import (
    StockRequestBasicSerializer,
)


class CarbonTransactionSerializer(serializers.Serializer):
    """Serializer to list carbon transactions in farmer profile"""
    number = serializers.CharField()
    trans_type = serializers.SerializerMethodField()
    date = serializers.DateTimeField()
    quantity = serializers.SerializerMethodField()
    connection = serializers.SerializerMethodField()

    def get_quantity(self, obj):
        """Get quantity based on transaction type"""
        quantity = obj._destination_quantity
        if obj.transaction_type != TRANSACTION_TYPE_EXTERNAL and \
            obj.type == INTERNAL_TRANS_TYPE_LOSS:
            quantity = obj._source_quantity
        return quantity

    def get_trans_type(self, obj):
        """
        Get transaction type based on certain conditions
        """
        return CARBON_TRANSACTION_TYPE_MAP[obj.transaction_type][obj.type]

    def _get_node_for_external_transaction(self, obj):
        """
        Helper method to determine the correct node based on transaction type.
        """
        try:
            node_id = self.context['request'].query_params.get('node')
            node = Node.objects.get(id=common_lib.decode(node_id))
        except:
            raise BadRequest("Invalid Node", send_to_sentry=False)
        if obj.source == node:
            return obj.destination
        return obj.source
            
    def get_connection(self, obj):
        """
        If the transaction is external:
        - If it's an incoming transaction, return the source node.
        - Otherwise, return the destination node.
        For non-external transactions, return None.
        """
        if obj.transaction_type != TRANSACTION_TYPE_EXTERNAL:
            return None

        # Determine the node based on transaction type
        node = self._get_node_for_external_transaction(obj)
        return NodeBasicSerializer(node).data


class CarbonExternalTransactionSerializer(serializers.ModelSerializer):
    """Serializer for creating carbon products external transaction"""

    id = custom_fields.IdencodeField(read_only=True)
    number = serializers.IntegerField(read_only=True)
    status = serializers.IntegerField(read_only=True)
    type = serializers.IntegerField(write_only=True)
    unit = serializers.IntegerField(write_only=True)
    transaction_type = serializers.IntegerField(read_only=True)
    node = custom_fields.IdencodeField(
        related_model=Node, 
        write_only=True
    )
    product = custom_fields.IdencodeField(
        related_model=Product, 
        write_only=True
    )
    quantity = custom_fields.RoundingDecimalField(
        max_digits=25, 
        decimal_places=3, 
        write_only=True, 
        min_value=0.01
    )
    batches = batch_serializers.SourceBatchSerializer(
        write_only=True, 
        many=True, 
        required=False
    )
    select_all_batches = serializers.BooleanField(
        default=False, 
        write_only=True
    )
    send_seperately = serializers.BooleanField(
        default=False, 
        write_only=True
    )
    transparency_request = custom_fields.IdencodeField(
        related_model=StockRequest,
        serializer=StockRequestBasicSerializer,
        required=False,
        source="stockrequest",
    )
    source = custom_fields.IdencodeField(
        read_only=True, 
        serializer=NodeBasicSerializer
    )
    source_wallet = custom_fields.IdencodeField(
        read_only=True, 
        serializer=NodeWalletSerializer
    )
    destination = custom_fields.IdencodeField(
        read_only=True, 
        serializer=NodeBasicSerializer
    )
    destination_wallet = custom_fields.IdencodeField(
        read_only=True, 
        serializer=NodeWalletSerializer
    )
    card_details = NodeCardSerializer(
        source="card", 
        read_only=True
    )
    card = custom_fields.IdencodeField(
        related_model=NodeCard, 
        required=False
    )
    source_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, 
        decimal_places=3, 
        read_only=True
    )
    destination_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, 
        decimal_places=3, 
        read_only=True
    )
    blockchain_address = serializers.CharField(read_only=True)
    created_on = custom_fields.UnixTimeField(required=False)
    date = serializers.DateTimeField(required=False)
    logged_time = serializers.DateTimeField(
        source="created_on", 
        read_only=True
    )
    claims = custom_fields.ManyToManyIdencodeField(
        serializer=product_claims.BatchClaimSerializer,
        source="get_claims",
        read_only=True,
    )
    is_created = serializers.BooleanField(
        default=True, 
        required=False
    )
    premiums = IssuedPremiumSerializer(
        allow_null=True,
        many=True,
        source="premium_paid",
        default=None,
        required=False,
    )
    force_create = serializers.BooleanField(
        default=False, 
        required=False
    )
    invoice = serializers.FileField(required=False)
    source_batches = serializers.SerializerMethodField("get_source_products")
    destination_batches = serializers.SerializerMethodField(
        "get_destination_products"
    )
    rejectable = serializers.SerializerMethodField("check_if_rejectable")
    remittance_type = serializers.SerializerMethodField()
    gtin = serializers.SerializerMethodField()
    is_batch_editable = serializers.SerializerMethodField()

    current_node = None

    class Meta:
        model = ExternalTransaction
        fields = (
            "id",
            "date",
            "batches",
            "select_all_batches",
            "send_seperately",
            "node",
            "product",
            "quantity",
            "unit",
            "price",
            "currency",
            "type",
            "blockchain_address",
            "wallet_type",
            "explorer_url",
            "source_wallet",
            "destination_wallet",
            "card",
            "source",
            "destination",
            "source_quantity",
            "destination_quantity",
            "number",
            "source_batches",
            "destination_batches",
            "logged_time",
            "transaction_type",
            "rejectable",
            "comment",
            "claims",
            "status",
            "invoice_number",
            "transparency_request",
            "created_on",
            "client_type",
            "verification_method",
            "is_created",
            "premiums",
            "force_create",
            "invoice",
            "buyer_ref_number",
            "seller_ref_number",
            "card_details",
            "archived",
            "remittance_type",
            "gtin",
            "is_batch_editable"
        )

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        super(CarbonExternalTransactionSerializer, self).__init__(*args, **kwargs)
        source_id = kwargs['data'].get("source")
        try:
            node = Node.objects.get(id=common_lib.decode(source_id))
        except:
            raise BadRequest("Source not found")
        self.current_node = node
    
    def check_if_rejectable(self, instance):
        """
        Transaction can only be rejected is it's batched have not been
        used.
        """
        if (
                instance.is_rejectable
                and instance.destination == self.current_node
        ):
            return True
        return False

    def get_transaction_direction(self, instance):
        """Textual representation of transaction type."""
        if instance.source == self.current_node:
            return "Sent Stock"
        elif instance.destination == self.current_node:
            return "Received Stock"
        else:
            return "Other"

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

    def get_buyer_supplier(self, node):
        """
        Unlike external transaction here current node will always be supplier
        """
        supplier = self.current_node
        buyer = node
        return buyer, supplier

    def validate_node(self, node):
        """Validate node."""
        if not node:
            raise serializers.ValidationError("Invalid Node ID")
        return node

    def validate(self, attrs):
        """
        Validate the data matches the transparency request that is attached
        and the batched attached are owned by the supplier company
        """
        if "node" in attrs.keys():
            buyer, supplier = self.get_buyer_supplier(attrs["node"])
        invalid_batches = []
        if "batches" in attrs:
            for batch in attrs["batches"]:
                if batch["batch"].node != supplier:
                    invalid_batches.append(batch["batch"].idencode)
        if invalid_batches:
            raise serializers.ValidationError(
                "%s does not own batch(s) %s"
                % (supplier.idencode, ", ".join(invalid_batches))
            )
        if "transparency_request" in attrs:
            try:
                assert (
                        attrs["transparency_request"].connection.buyer == buyer
                ), "Buyer Mismatch"
                assert (
                        attrs["transparency_request"].connection.supplier
                        == supplier
                ), "Supplier mismatch"
                assert (
                        attrs["transparency_request"].product == attrs[
                    "product"]
                ), "Product Mismatch"
                assert (
                        attrs["transparency_request"].quantity == attrs[
                    "quantity"]
                ), "Quantity Mismatch"
                assert (
                        attrs["transparency_request"].unit == attrs["unit"]
                ), "Unit mismatch"
                assert (
                        attrs["transparency_request"].currency == attrs[
                    "currency"]
                ), "Currency Mismatch"
                if attrs["transparency_request"].price:
                    assert (
                            attrs["transparency_request"].price == attrs[
                        "price"]
                    ), "Price Mismatch"
            except AssertionError as e:
                raise serializers.ValidationError(
                    f"Transparency request mismatch. {e}."
                )
        return attrs

    def prepare_batches(self, validated_data):
        """
        If product A, B, C are sent to another company as product D, some
        internal transaction are handled by the system.

        A, B, C are converted to D as an internal processing transaction
        and the resulting batch of product D is then sent to the buyer.
        """
        incoming_type = trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
        select_all_batches = validated_data.pop("select_all_batches", False)

        if validated_data["type"] != incoming_type:
            batches = validated_data.pop("batches", [])
            send_seperately = validated_data.get("send_seperately", False)
            
            if select_all_batches:
                self._get_only_batches_to_batches(batches)
            if (
                    (len(batches) > 1 and not send_seperately) 
                    or batches[0]["batch"].product != validated_data["product"]
            ):
                int_trans = self.create_intetrnal_transaction(
                    batches, validated_data)
                result_batches = int_trans.result_batches.all()
                validated_data["batches"] = [
                    {
                        "batch": result_batch,
                        "quantity": result_batch.initial_quantity
                    } for result_batch in result_batches]
            else:
                validated_data["batches"] = batches

        return validated_data
    
    def create_intetrnal_transaction(self, batches, validated_data):
        """Create internal transaction for the batches."""
        source_batches = [
                    {"batch": i["batch"].idencode, "quantity": i["quantity"]}
                    for i in batches
        ]
        int_tran_data = {
            "type": trans_constants.INTERNAL_TRANS_TYPE_PROCESSING,
            "mode": trans_constants.TRANSACTION_MODE_SYSTEM,
            "source_batches": source_batches,
            "comment": validated_data.get("comment", ""),
            "destination_batches": [
                {
                    "product": validated_data["product"].idencode,
                    "quantity": validated_data["quantity"],
                    "unit": validated_data["unit"],
                }
            ],
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
        return int_tran_serializer.save()

    @staticmethod
    def prepare_incoming_batches(**kwargs) -> dict:
        """
        If the transaction is incoming, the batches will first be created
        for the farmer before transferring it to the supplier.

        The resultant stock of any farmer at any point in time will be
        zero.
        """
        batch = Batch.objects.create(
            node=kwargs["source"],
            product=kwargs["product"],
            name="Created for transferring to %s"
                 % kwargs["destination"].full_name,
            initial_quantity=kwargs["quantity"],
            current_quantity=kwargs["quantity"],
            unit=kwargs["unit"],
            type=prod_constants.BATCH_TYPE_INTERMEDIATE,
        )
        return [{"batch": batch, "quantity": batch.initial_quantity}]
    
    def create_source_destination_batches(
            self, 
            send_seperately=False, 
            **kwargs
        ):
        """Create source and destination batches for the transaction."""
        transaction = kwargs.get("transaction")
        user = kwargs.get("user")
        product = kwargs.get("product")
        name = kwargs.get("name")
        buyer = kwargs.get("buyer")
        unit = kwargs.get("unit")
        quantity = kwargs.get("quantity")
        comment = kwargs.get("comment")
        batches = kwargs.get("batches")

        selected_batches = []
        
        for batch_item in batches:
            batch = batch_item["batch"]
            qty = batch_item["quantity"]
            SourceBatch.objects.create(
                transaction=transaction, 
                batch=batch, 
                quantity=qty, 
                creator=user, 
                updater=user
            )
            batch.current_quantity -= qty
            selected_batches.append(batch)

            if batch.source_transaction:
                transaction.add_parent(batch.source_transaction)
            # Creating result batch.
            
            new_batch = Batch.objects.create(
                product=product, node=buyer,
                initial_quantity=qty if send_seperately else quantity, 
                current_quantity=qty if send_seperately else quantity, 
                unit=unit, name=name, creator=user, updater=user, 
                source_transaction=transaction, note=comment)
            new_batch.parents.add(batch)
            new_batch.update_batch_farmers()

        Batch.objects.bulk_update(selected_batches, ["current_quantity"])

    @staticmethod
    def filter_for_duplicate_txn(validated_data, **kwargs) -> tuple:
        """Filter out or create transaction with created flag."""
        created = False
        transactions = ExternalTransaction.objects.filter(**validated_data)
        if kwargs.get("product", None):
            transactions = transactions.filter(
                source_batches__product=kwargs["product"]
            )
        if transactions:
            transaction = transactions.first()
        else:
            transaction = ExternalTransaction.objects.create(**validated_data)
            created = True
        return transaction, created

    @django_transaction.atomic
    def create(self, validated_data):
        """
        Overriding the create method.
        The function check the transaction is duplicate or not and if
        not then create External transaction.
        """

        if "node" in validated_data.keys():
            connected_nodes = self.current_node.get_connections()
            if not validated_data["node"] in connected_nodes:
                raise BadRequest(
                    f"Only connected companies can create transaction.: "
                    f"{validated_data['node']} not in {connected_nodes}"
                )
        force_create = validated_data.pop("force_create", None)
        if "created_on" in validated_data.keys():
            validated_data["date"] = validated_data["created_on"]
        try:
            current_user = self.context["request"].user
        except KeyError:
            current_user = self.context["user"]
        buyer, supplier = self.get_buyer_supplier(validated_data["node"])

        node = validated_data.pop("node")

        validated_data["creator"] = current_user
        validated_data["updater"] = current_user
        validated_data["source"] = supplier
        validated_data["destination"] = buyer

        validated_data = self.prepare_batches(validated_data)
        send_seperately = validated_data.pop("send_seperately", False)
        transparency_request = validated_data.pop("stockrequest", None)
        batch_data = validated_data.pop("batches", None)
        product = validated_data.pop("product")
        quantity = validated_data.pop("quantity")
        unit = validated_data.pop("unit")
        name = validated_data.pop(
            "name", "Purchased from %s" % supplier.full_name
        )
        validated_data.pop("is_created", None)

        validated_data.pop("premium_paid", None)
        # if force_create is true, create duplicate transaction
        # in bulk transaction upload scenario.
        if force_create:
            created = True
            transaction = ExternalTransaction.objects.create(**validated_data)
        else:
            # Checking duplicate transaction with product or create new.
            transaction, created = self.filter_for_duplicate_txn(
                validated_data, product=product
            )

        transaction.is_created = True
        if not created:
            transaction.is_created = False
            return transaction

        type_incoming = trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
        if not batch_data and validated_data["type"] == type_incoming:
            batch_data = self.prepare_incoming_batches(
                source=validated_data["source"],
                product=product,
                destination=validated_data["destination"],
                quantity=quantity,
                unit=unit,
            )

        validated_data["node"] = node
        
        data = {
            "transaction" : transaction,
            "user" : current_user,
            "product" : product,
            "name" : name,
            "buyer" : buyer,
            "unit": unit,
            "quantity": quantity,
            "comment" : validated_data.get("comment", ""),
            "batches" : batch_data,
        }
        
        self.create_source_destination_batches(send_seperately, **data)

        if product.type == prod_constants.PRODUCT_TYPE_LOCAL:
            product.owners.add(transaction.destination)
        status_completed = trr_constants.TRANSPARENCY_REQUEST_STATUS_COMPLETED
        if transparency_request:
            transparency_request.transaction = transaction
            transparency_request.updater = current_user
            transparency_request.status = status_completed
            transparency_request.save()
        transaction.result_batches.update(
            buyer_ref_number=validated_data.get("buyer_ref_number", None),
            seller_ref_number=validated_data.get("seller_ref_number", None),
        )

        if created:
            django_transaction.on_commit(
                lambda: self.post_commit(
                    transaction, supplier=supplier, buyer=buyer
                )
            )
        return transaction

    @staticmethod
    def post_commit(transaction, **kwargs):
        """To perform function post_commit."""
        transaction.source_wallet = kwargs[
            "supplier"
        ].setup_blockchain_account()
        transaction.destination_wallet = kwargs[
            "buyer"
        ].setup_blockchain_account()
        transaction.save()
        transaction_follow_up.delay(transaction.id)

    def to_representation(self, instance):
        """Quantity and product to be shown in the interface will different for
        source and destination companies."""
        data = super(CarbonExternalTransactionSerializer, self).to_representation(
            instance
        )
        try:
            node = self.context["view"].kwargs["node"]
        except Exception:
            node = self.context["node"]
        if node == instance.source:
            if instance.type == trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL
            else:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_OUTGOING
            data["quantity"] = data["source_quantity"]
            if "source_batches" in data.keys():
                data["products"] = data["source_batches"]
            common_lib._pop_out_from_dictionary(
                data,
                [
                    "source_quantity",
                    "destination_quantity",
                ],
            )
        elif node == instance.destination:
            if instance.type == trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL
            else:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
            data["quantity"] = data["destination_quantity"]
            data["products"] = data["destination_batches"]
            common_lib._pop_out_from_dictionary(
                data,
                [
                    "source_quantity",
                    "destination_quantity",
                ],
            )
            nsc = instance.source.nodesupplychain_set.get(
                node=instance.source,
                supply_chain=instance.source_batches
                .first()
                .product.supply_chain,
            )

            primary_operation = {
                "id": (nsc.primary_operation.idencode
                       if nsc.primary_operation else None),
                "name": (nsc.primary_operation.name
                         if nsc.primary_operation else None),
            }
            data["source"]["primary_operation"] = primary_operation
        data["consumer_interface_url"] = self._get_consumer_interface_url(node)
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

    def _get_only_batches_to_batches(self, only_changed_batches):
        """
        Retrieves batches associated with a specific node that are not
        already present in the 'only_changed_batches' list.

        This method is responsible for finding batches associated with a
        specific node that are not present in the
        'only_changed_batches' list. The 'only_changed_batches' list should
        contain dictionaries with 'batch' and 'quantity' keys.

        Args:
            only_changed_batches (list): A list of dictionaries, each
            containing 'batch' and 'quantity' keys.
        """
        if self.current_node:
            batch_ids = [
                batch_data["batch"].pk for batch_data in only_changed_batches
            ]
            batch_qs = Batch.objects.filter(
                Q(node_id=self.current_node.id, current_quantity__gt=0)
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
    
    def get_remittance_type(self, obj):
        """Get remittance type from extra fields."""
        for field in obj.extra_fields:
            remittance_type = next(
                (
                    value["value"]
                    for value in field.get("values", [])
                    if value.get(
                        "field_details", {}
                    ).get("key") == "payment_method"
                ),
                None
            )
            if remittance_type:
                return remittance_type        
        return None
    
    def get_gtin(self, obj):
        """
        Return the GTIN of the first batch, or an empty string if not 
        available.
        """
        batch = obj.result_batches.only('gtin').first()
        return batch.gtin if batch and batch.gtin else ""
    
    def get_is_batch_editable(self, obj):
        """
        Return whether the batch is editable or not
        """
        try:
            node = self.context["view"].kwargs["node"]
        except Exception:
            node = self.context["node"]
        batch = obj.result_batches.values('node').first()
        if batch is None or batch['node'] != node.id:
            return False
        return True


class CarbonInternalTransactionSerializer(serializers.ModelSerializer):
    """Serializer to create internal transactions."""

    # Write only fields for creation
    user = custom_fields.KWArgsObjectField(write_only=True)
    node = custom_fields.IdencodeField(write_only=True, related_model=Node)
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
    gtin = serializers.SerializerMethodField()
    is_batch_editable = serializers.SerializerMethodField()

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
            "archived",
            "gtin",
            "is_batch_editable"
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
        validated_data['source_batches'] = validated_data.get(
            'source_batches', [])
        if select_all_batches:
            self._get_only_batches_to_batches(
                validated_data["source_batches"], 
                validated_data["node"]
            )

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
    
    def _get_only_batches_to_batches(self, only_changed_batches, node):
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
    
    def get_gtin(self, obj):
        """
        Return the GTIN of the first batch, or an empty string if not 
        available.
        """
        batch = obj.result_batches.only('gtin').first()
        return batch.gtin if batch and batch.gtin else ""
    
    def get_is_batch_editable(self, obj):
        """
        Return whether the batch is editable or not
        """
        try:
            node = self.context["view"].kwargs["node"]
        except Exception:
            node = self.context["node"]
        batch = obj.result_batches.values('node').first()
        if batch is None or batch['node'] != node.id:
            return False
        return True