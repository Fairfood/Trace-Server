"""Serializers for external transactions."""
from collections import OrderedDict

from common import library as common_lib
from common.drf_custom import fields as custom_fields
from common.exceptions import BadRequest
from django.conf import settings
from django.db import transaction as django_transaction
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from v2.claims.models import AttachedBatchClaim
from v2.claims.serializers import product_claims
from v2.communications import constants as notif_constants
from v2.communications.models import Notification
from v2.products import constants as prod_constants
from v2.products.models import Batch
from v2.products.models import Product
from v2.products.serializers import batch as batch_serializers
from v2.products.serializers import product as prods_serializers
from v2.projects.models import NodeCard
from v2.projects.serializers.project import NodeCardSerializer
from v2.projects.serializers.project import ProjectPremiumSerializer
from v2.supply_chains import constants as sc_constants
from v2.supply_chains.models import Node
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.supply_chains.serializers.public import NodeWalletSerializer
from v2.transactions import constants as trans_constants
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import SourceBatch
from v2.transactions.tasks import transaction_follow_up
from v2.transparency_request import constants as trr_constants
from v2.transparency_request.models import StockRequest
from v2.transparency_request.serializers.public import (
    StockRequestBasicSerializer,
)

from ...accounts.serializers.user import UserListSerializer
from ...dashboard.models import CITheme
from .internal import InternalTransactionSerializer


class IssuedPremiumSerializer(serializers.Serializer):
    """Serializer to serialize the premium issued for a transaction."""

    premium = ProjectPremiumSerializer()
    amount = serializers.FloatField()

    class Meta:
        fields = "__all__"


class ExternalTransactionSerializer(serializers.ModelSerializer):
    """Serializer for creating external transaction as well as getting
    details."""

    type = serializers.IntegerField(write_only=True)
    node = custom_fields.IdencodeField(related_model=Node, write_only=True)
    product = custom_fields.IdencodeField(
        related_model=Product, write_only=True
    )
    quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, write_only=True, min_value=0.01
    )
    unit = serializers.IntegerField(write_only=True)
    batches = batch_serializers.SourceBatchSerializer(
        write_only=True, many=True, required=False
    )
    select_all_batches = serializers.BooleanField(default=False, 
                                                  write_only=True)
    
    send_seperately = serializers.BooleanField(default=False, 
                                               write_only=True)

    transparency_request = custom_fields.IdencodeField(
        related_model=StockRequest,
        serializer=StockRequestBasicSerializer,
        required=False,
        source="stockrequest",
    )

    # Read only fields for output
    id = custom_fields.IdencodeField(read_only=True)
    number = serializers.IntegerField(read_only=True)
    status = serializers.IntegerField(read_only=True)

    source = custom_fields.IdencodeField(
        read_only=True, serializer=NodeBasicSerializer
    )
    source_wallet = custom_fields.IdencodeField(
        read_only=True, serializer=NodeWalletSerializer
    )
    destination = custom_fields.IdencodeField(
        read_only=True, serializer=NodeBasicSerializer
    )
    destination_wallet = custom_fields.IdencodeField(
        read_only=True, serializer=NodeWalletSerializer
    )

    card_details = NodeCardSerializer(source="card", read_only=True)
    card = custom_fields.IdencodeField(related_model=NodeCard, required=False)

    source_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True
    )
    destination_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True
    )
    source_batches = serializers.SerializerMethodField(
        "get_source_products", read_only=True
    )
    destination_batches = serializers.SerializerMethodField(
        "get_destination_products", read_only=True
    )
    blockchain_address = serializers.CharField(read_only=True)
    created_on = custom_fields.UnixTimeField(required=False)
    date = serializers.DateTimeField(required=False)
    logged_time = serializers.DateTimeField(
        source="created_on", read_only=True
    )
    transaction_type = serializers.IntegerField(read_only=True)
    rejectable = serializers.SerializerMethodField(
        "check_if_rejectable", read_only=True
    )
    claims = custom_fields.ManyToManyIdencodeField(
        serializer=product_claims.BatchClaimSerializer,
        source="get_claims",
        read_only=True,
    )
    is_created = serializers.BooleanField(default=True, required=False)
    premiums = IssuedPremiumSerializer(
        allow_null=True,
        many=True,
        source="premium_paid",
        default=None,
        required=False,
    )
    force_create = serializers.BooleanField(default=False, required=False)
    invoice = serializers.FileField(required=False)
    remittance_type = serializers.SerializerMethodField()

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
            "remittance_type"
        )

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        super(ExternalTransactionSerializer, self).__init__(*args, **kwargs)
        try:
            self.current_node = self.context["view"].kwargs["node"]
        except Exception:
            self.current_node = self.context["node"]

    def check_if_rejectable(self, instance):
        """Transaction can only be rejected is it's batched have not been
        used."""
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

    def validate_buyer_supplier(self, buyer, supplier):
        """Verify that incoming transaction can only be done from a farmer and
        that the connection between the nodes exist in the supply chain before
        doing a transaction."""
        if (
                int(self.initial_data["type"])
                == trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
        ):
            if supplier.type != sc_constants.NODE_TYPE_FARM:
                raise serializers.ValidationError(
                    "Incoming transaction can only be created from farmer"
                )

        Product.objects.get(
            id=common_lib._decode(self.initial_data["product"])
        ).supply_chain

    def get_buyer_supplier(self, node):
        """Get buyer and supplier based on transaction direction."""
        if (
                int(self.initial_data["type"])
                == trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
        ):
            supplier = node
            buyer = self.current_node
        else:
            supplier = self.current_node
            buyer = node
        return buyer, supplier

    def validate_node(self, node):
        """Validate node."""
        if not node:
            raise serializers.ValidationError("Invalid Node ID")
        buyer, supplier = self.get_buyer_supplier(node)
        if (
                int(self.initial_data["type"])
                != trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL
        ):
            self.validate_buyer_supplier(buyer, supplier)
        return node

    def validate(self, attrs):
        """Validate the data matches the transparency request that is attached.

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
        """If product A, B, C are sent to another company as product D, some
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
        """If the transaction is incoming, the batches will first be created
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
    
    def create_source_destination_batches(self, 
                                          send_seperately=False, 
                                          **kwargs):
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
            
            
            SourceBatch.objects.create(transaction=transaction, batch=batch, 
                            quantity=qty, creator=user, updater=user)
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
        """Overriding the create method.

        The function check the transaction is duplicate or not and if
        not then create External transaction.
        """

        if "node" in validated_data.keys():
            supply_chain = Product.objects.get(
                id=common_lib._decode(self.initial_data["product"])
            ).supply_chain
            try:
                node = self.context["view"].kwargs["node"]
            except KeyError:
                node = self.context["node"]
            connected_nodes = node.get_connections(supply_chain=supply_chain)
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
        data = super(ExternalTransactionSerializer, self).to_representation(
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



class ExternalTransactionListSerializer(serializers.ModelSerializer):
    """Serializer for details in the list page of external transactions."""

    id = custom_fields.IdencodeField(read_only=True)
    creator = custom_fields.IdencodeField(
        read_only=True, serializer=UserListSerializer
    )
    number = serializers.IntegerField(read_only=True)
    source = custom_fields.IdencodeField(
        read_only=True, serializer=NodeBasicSerializer
    )
    destination = custom_fields.IdencodeField(
        read_only=True, serializer=NodeBasicSerializer
    )
    source_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True
    )
    destination_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True
    )
    source_products = custom_fields.ManyToManyIdencodeField(
        serializer=prods_serializers.ProductSerializer, read_only=True
    )
    destination_products = custom_fields.ManyToManyIdencodeField(
        serializer=prods_serializers.ProductSerializer, read_only=True
    )
    result_batches = custom_fields.ManyToManyIdencodeField(read_only=True)
    blockchain_address = serializers.CharField(read_only=True)
    date = serializers.DateTimeField(required=False)
    # date = serializers.DateField(
    #     format="%d %b %Y", input_formats=["%Y-%m-%d"],
    #     required=False)
    rejectable = serializers.SerializerMethodField(
        "check_if_rejectable", read_only=True
    )

    class Meta:
        model = ExternalTransaction
        fields = (
            "id",
            "number",
            "source",
            "destination",
            "source_quantity",
            "destination_quantity",
            "source_products",
            "destination_products",
            "blockchain_address",
            "date",
            "price",
            "currency",
            "rejectable",
            "result_batches",
            "buyer_ref_number",
            "seller_ref_number",
            "creator",
            "archived"
        )

    def check_if_rejectable(self, instance):
        """To perform function check_if_rejectable."""
        try:
            current_node = self.context["view"].kwargs["node"]
            if instance.is_rejectable and instance.destination == current_node:
                return True
            return False
        except KeyError:
            return False

    def to_representation(self, instance):
        """To perform function to_representation."""
        data = super(
            ExternalTransactionListSerializer, self
        ).to_representation(instance)
        try:
            node = self.context["view"].kwargs["node"]
        except Exception:
            node = self.context["node"]
        if node == instance.source:
            if instance.type == trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL
            else:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_OUTGOING
            data["connection"] = data["destination"]
            data["quantity"] = data["source_quantity"]
            data["products"] = data["source_products"]
            common_lib._pop_out_from_dictionary(
                data,
                [
                    "source",
                    "destination",
                    "source_quantity",
                    "source_products",
                    "destination_quantity",
                    "destination_products",
                ],
            )
        elif node == instance.destination:
            if instance.type == trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL
            else:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
            data["connection"] = data["source"]
            data["quantity"] = data["destination_quantity"]
            data["products"] = data["destination_products"]
            common_lib._pop_out_from_dictionary(
                data,
                [
                    "source",
                    "destination",
                    "source_quantity",
                    "source_products",
                    "destination_quantity",
                    "destination_products",
                ],
            )
        return data


class ExternalTransactionRejectionSerializer(serializers.Serializer):
    """Serializer to reject an external transaction."""

    user = custom_fields.KWArgsObjectField(write_only=True)
    node = custom_fields.KWArgsObjectField(write_only=True)
    pk = custom_fields.KWArgsObjectField(write_only=True)
    comment = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """To perform function validate."""
        external_transaction = ExternalTransaction.objects.get(id=attrs["pk"])
        attrs["batches"] = []
        for result_batch in external_transaction.result_batches.all():
            if result_batch.initial_quantity != result_batch.current_quantity:
                raise BadRequest("Transaction cannot be rejected")
            attrs["batches"].append(
                {
                    "batch": result_batch.idencode,
                    "quantity": result_batch.initial_quantity,
                }
            )
        attrs["external_transaction"] = external_transaction
        node = self.context["view"].kwargs["node"]
        if not external_transaction.destination == node:
            raise BadRequest("Only destination node can reject transaction.")
        return attrs

    def remove_txn_notifications(self, external_transaction):
        """Function for remove verifier notifications when reject
        transaction."""
        attached_claims = AttachedBatchClaim.objects.filter(
            batch__source_transaction__id=external_transaction.id
        )
        # remove all notifications related to this attached claim.
        for attached_claim in attached_claims:
            notifications = Notification.objects.filter(
                event_id=common_lib._encode(attached_claim.id),
                type=notif_constants.NOTIF_TYPE_RECEIVE_VERIFICATION_REQUEST,
            )
            notifications.delete()
        return True

    @django_transaction.atomic
    def create(self, validated_data):
        """To perform function create."""
        external_transaction = validated_data["external_transaction"]
        self.remove_txn_notifications(external_transaction)
        external_transaction.status = (
            trans_constants.TRANSACTION_STATUS_DECLINED
        )
        external_transaction.comment = validated_data.get("comment", "")
        external_transaction.save()
        rslt_batch = external_transaction.result_batches.first()
        transaction_data = {
            "type": trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL,
            "node": external_transaction.source.idencode,
            "price": external_transaction.price,
            "currency": external_transaction.currency,
            "product": rslt_batch.product.idencode,
            "quantity": rslt_batch.initial_quantity,
            "unit": external_transaction.result_batches.first().unit,
            "batches": validated_data["batches"],
            "name": "Sending back to %s"
                    % external_transaction.source.full_name,
            "comment": validated_data.get("comment", ""),
        }
        ext_serializer = ExternalTransactionSerializer(
            data=transaction_data, context=self.context
        )
        if not ext_serializer.is_valid():
            raise serializers.ValidationError(ext_serializer.errors)
        ext_serializer.save()
        # for batch in ext_trans.result_batches.all():
        #     batch.inherit_claims()
        return True

    def to_representation(self, instance):
        """To perform function to_representation."""
        return {"status": True, "message": "Transaction rejected and reversed"}
