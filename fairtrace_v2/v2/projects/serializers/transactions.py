"""Serializers for project details."""
from babel.numbers import format_decimal

from common import exceptions as comm_exe
from common import library as common_lib
from common.drf_custom import fields as custom_fields
from django.utils.translation import gettext as _
from rest_framework import serializers
from v2.claims.serializers import product_claims
from v2.products.models import Batch
from v2.products.serializers import batch as batch_serializers
from v2.products.serializers import product as prods_serializers
from v2.projects import constants as project_const
from v2.projects.constants import BASE_TRANSACTION
from v2.projects.models import Payment
from v2.projects.models import PremiumOption
from v2.projects.models import ProjectPremium
from v2.projects.serializers.project import NodeCardSerializer
from v2.projects.serializers.project import ProjectPremiumSerializer
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.transactions import constants as trans_constants
from v2.transactions import models as trans_model
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import Transaction
from v2.transactions.serializers import internal as internal_serializers
from v2.transactions.serializers.external import ExternalTransactionSerializer


class IssuedPremiumSerializer(serializers.Serializer):
    """Serializer to serialize the premium issued for a transaction."""

    id = custom_fields.IdencodeField(related_model=Payment, read_only=True)
    premium = custom_fields.IdencodeField(
        related_model=ProjectPremium, serializer=ProjectPremiumSerializer
    )
    amount = serializers.FloatField(min_value=0.01)
    selected_option = custom_fields.IdencodeField(
        related_model=PremiumOption, required=False
    )

    class Meta:
        fields = "__all__"


class AppTransactionSerializer(ExternalTransactionSerializer):
    """Serializer for both incoming and outgoing transactions."""

    created_on = custom_fields.UnixTimeField()
    premiums = IssuedPremiumSerializer(
        allow_null=True, many=True, source="premium_paid"
    )
    card_id = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    verification_method = serializers.IntegerField(required=False)
    verification_latitude = serializers.FloatField(required=False)
    verification_longitude = serializers.FloatField(required=False)
    client_type = serializers.IntegerField(default=trans_constants.CLIENT_APP)
    base_payment_id = serializers.SerializerMethodField()

    class Meta(ExternalTransactionSerializer.Meta):
        fields = (
            "id",
            "type",
            "date",
            "batches",
            "node",
            "product",
            "quantity",
            "unit",
            "price",
            "currency",
            "source",
            "destination",
            "source_quantity",
            "destination_quantity",
            "number",
            "source_batches",
            "destination_batches",
            "created_on",
            "premiums",
            "invoice",
            "card_id",
            "card",
            "product_price",
            "quality_correction",
            "verification_method",
            "client_type",
            "verification_latitude",
            "verification_longitude",
            "is_created",
            "extra_fields",
            "base_payment_id",
            "card_details",
            "invoice_number"
        )
        extra_kwargs = {
            "date": {"required": False},
        }

    def get_base_payment_id(self, instance):
        """Get the ID of the base payment associated with the given transaction
        instance.

        This method retrieves the ID of the most recent base payment associated
        with the transaction. It filters the transaction payments based on the
        payment type (BASE_TRANSACTION) and returns the ID of the last payment
        in the filtered queryset.

        Parameters:
        - instance: The transaction instance.

        Returns:
        - int or None: The ID of the base payment, or None if no base payment
            is found.
        """
        base_payment = (
            instance.transaction_payments.filter(payment_type=BASE_TRANSACTION)
            .only("id")
            .last()
        )
        if base_payment:
            return base_payment.idencode
        return None

    def validate(self, attrs):
        """To perform function validate."""
        # Adding dial code for phone number
        attrs = super(AppTransactionSerializer, self).validate(attrs)
        if attrs["type"] == trans_constants.EXTERNAL_TRANS_TYPE_OUTGOING:
            if attrs["premiums"]:
                raise serializers.ValidationError(
                    "Premium not issued for outgoing transactions"
                )

        # Validating card_id
        if "card" not in attrs:
            card_id = attrs.pop("card_id", "")
            node = attrs["node"]
            cards = node.cards.filter(card_id=card_id)
            if card_id and not cards.exists():
                raise serializers.ValidationError(
                    "Invalid Card ID. Transaction not authorized"
                )
            attrs["card"] = cards.first()
        return attrs

    def create_premium(self, premiums, transaction, node):
        """Function for create transaction premium."""
        for premium in premiums:
            if premium["amount"] < 0.01:
                continue
            Payment.objects.get_or_create(
                premium=premium["premium"],
                amount=premium["amount"],
                selected_option=premium.get("selected_option"),
                transaction=transaction,
            )

    def create(self, validated_data):
        """Overriding the create method.

        The function create transaction and transaction premium.
        """
        node = validated_data["node"]
        created_on = validated_data.pop("created_on")
        premiums = validated_data.pop("premium_paid")
        validated_data["date"] = created_on.strftime("%Y-%m-%d %H:%M:%S")
        transaction = super(AppTransactionSerializer, self).create(
            validated_data
        )
        transaction.created_on = created_on
        transaction.save()
        self.create_premium(premiums, transaction, node)
        return transaction

    def get_source_products(self, instance):
        """Product data of source batches."""
        data = []
        for source_batch in instance.source_batch_objects.all():
            product_data = prods_serializers.ProductSerializer(
                source_batch.batch.product
            ).data
            product_data["product_id"] = product_data["id"]
            product_data["id"] = source_batch.batch.idencode
            product_data["quantity"] = source_batch.quantity
            product_data["number"] = source_batch.batch.number
            product_data["unit"] = source_batch.batch.unit
            data.append(product_data)
        return data

    def get_destination_products(self, instance):
        """Product data of destination batches."""
        data = []
        for result_batch in instance.result_batches.all():
            product_data = prods_serializers.ProductSerializer(
                result_batch.product
            ).data
            product_data["product_id"] = product_data["id"]
            product_data["id"] = result_batch.idencode
            product_data["quantity"] = result_batch.initial_quantity
            product_data["number"] = result_batch.number
            product_data["unit"] = result_batch.unit
            product_data["current_quantity"] = result_batch.current_quantity
            data.append(product_data)
        return data

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
            common_lib._pop_out_from_dictionary(
                data, ["source_quantity", "destination_quantity"]
            )
        elif node == instance.destination:
            if instance.type == trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL
            else:
                data["type"] = trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
            data["quantity"] = data["destination_quantity"]

            common_lib._pop_out_from_dictionary(
                data, ["source_quantity", "destination_quantity"]
            )
        if data["type"] != trans_constants.EXTERNAL_TRANS_TYPE_INCOMING:
            common_lib._pop_out_from_dictionary(data, ["destination_batches"])
        return data


class TransactionInvoiceSerializer(serializers.ModelSerializer):
    """Serializer to update transaction invoice."""

    invoice = serializers.FileField()

    class Meta:
        model = Transaction
        fields = ("invoice", "invoice_number")


class OpenTransactionSerializer(serializers.ModelSerializer):
    """Serializer for creating external transaction as well as getting
    details."""

    quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, write_only=True
    )
    unit = serializers.IntegerField(write_only=True)
    product = prods_serializers.ProductSerializer(required=False)
    # Read only fields for output
    id = custom_fields.IdencodeField(read_only=True)
    status = serializers.IntegerField(read_only=True)
    destination_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True
    )
    created_on = custom_fields.UnixTimeField(required=False)
    date = serializers.DateTimeField(required=False)
    premiums = IssuedPremiumSerializer(
        allow_null=True, many=True, source="premium_paid"
    )

    class Meta:
        model = ExternalTransaction
        fields = (
            "id",
            "date",
            "quantity",
            "unit",
            "product",
            "unit",
            "price",
            "destination",
            "destination_quantity",
            "status",
            "created_on",
            "premiums",
            "extra_fields",
        )

    def _numeric_to_language_format(self, language, data):
        """To perform function _numeric_to_language_format."""
        data["price"] = format_decimal(data["price"], locale=language)
        data["total_price"] = format_decimal(
            data["total_price"], locale=language
        )
        data["destination_quantity"] = format_decimal(
            data["destination_quantity"], locale=language
        )
        return True

    def to_representation(self, instance):
        """Convert the instance to a representation suitable for serialization.

        This method is responsible for converting the given instance to a
        representation that can be serialized and returned in the API response.
        It applies specific formatting and modifications to the data before
        returning it.

        Parameters:
        - instance: The instance to be serialized.

        Returns:
        - dict: The serialized representation of the instance.
        """
        language = self.context["view"].kwargs["language"]
        data = super(OpenTransactionSerializer, self).to_representation(
            instance
        )
        data["total_price"] = 0
        data["id"] = common_lib._encrypt(str(instance.id))
        data["destination"] = instance.destination.full_name
        data["date_str"] = _(instance.date.strftime("%d %B, %Y"))
        if "premiums" in data.keys():
            for i in data["premiums"]:
                data["total_price"] += i["amount"]
                i["amount"] = format_decimal(i["amount"], locale=language)
        self._numeric_to_language_format(language, data)
        return data


class OpenTransactionDetailsSerializer(serializers.ModelSerializer):
    """Serializer for getting transaction details."""

    quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, write_only=True
    )
    unit = serializers.IntegerField(write_only=True)
    product = prods_serializers.ProductSerializer(required=False)
    destination_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True
    )
    created_on = custom_fields.UnixTimeField(required=False)
    date = serializers.DateTimeField(required=False)
    verification_method = serializers.IntegerField(required=False)
    premiums = IssuedPremiumSerializer(
        allow_null=True, many=True, source="premium_paid"
    )

    class Meta:
        model = ExternalTransaction
        fields = (
            "id",
            "date",
            "quantity",
            "unit",
            "product",
            "quantity",
            "unit",
            "price",
            "destination",
            "destination_quantity",
            "created_on",
            "verification_method",
            "premiums",
            "extra_fields",
        )

    def _numeric_to_language_format(self, language, data):
        """To perform function _numeric_to_language_format."""
        data["price"] = format_decimal(data["price"], locale=language)
        data["total_price"] = format_decimal(
            data["total_price"], locale=language
        )
        data["destination_quantity"] = format_decimal(
            data["destination_quantity"], locale=language
        )
        return True

    def to_representation(self, instance):
        """To perform function to_representation."""
        language = self.context["language"]
        data = super(OpenTransactionDetailsSerializer, self).to_representation(
            instance
        )
        data["total_price"] = 0
        data["id"] = common_lib._encrypt(str(instance.id))
        data["destination"] = instance.destination.full_name
        if "premiums" in data.keys():
            for i in data["premiums"]:
                data["total_price"] += i["amount"]
                i["amount"] = format_decimal(i["amount"], locale=language)
        data["total_price"] += float(data["price"])
        data["date_str"] = _(instance.date.strftime("%d %B, %Y"))
        self._numeric_to_language_format(language, data)
        return data


class AppSentTransactionSerializer(ExternalTransactionSerializer):
    """Serializer for create both external and internal transactions. if
    transaction is partial create internal loss transaction.

    created_on      : created datetime when app is offline.
    is_bal_loss     : if balance is loss in transaction return a
                      boolean true.
    loss_transaction: field for return loss transaction details.
    """

    created_on = custom_fields.UnixTimeField()
    batches = batch_serializers.AppSourceBatchSerializer(
        write_only=True, many=True
    )
    card_id = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    verification_method = serializers.IntegerField(required=False)
    verification_latitude = serializers.FloatField(
        required=True, write_only=True
    )
    verification_longitude = serializers.FloatField(
        required=True, write_only=True
    )
    batches = batch_serializers.SourceBatchSerializer(
        write_only=True, many=True, required=True
    )
    is_bal_loss = serializers.BooleanField(required=False, write_only=True)
    loss_transaction = internal_serializers.InternalTransactionSerializer(
        read_only=True
    )
    client_type = serializers.IntegerField(default=trans_constants.CLIENT_APP)
    premiums = IssuedPremiumSerializer(
        allow_null=True, many=True, source="premium_paid", required=False
    )
    source_batch = serializers.ListField(required=False, allow_empty=False)
    base_payment_id = serializers.SerializerMethodField()

    class Meta(ExternalTransactionSerializer.Meta):
        fields = (
            "id",
            "type",
            "date",
            "batches",
            "node",
            "product",
            "quantity",
            "unit",
            "price",
            "currency",
            "source",
            "destination",
            "source_quantity",
            "destination_quantity",
            "number",
            "source_batch",
            "destination_batches",
            "created_on",
            "invoice",
            "card_id",
            "card",
            "product_price",
            "quality_correction",
            "premiums",
            "verification_method",
            "client_type",
            "is_bal_loss",
            "loss_transaction",
            "is_created",
            "extra_fields",
            "verification_longitude",
            "verification_latitude",
            "base_payment_id",
            "card_details",
            "invoice_number"
        )
        extra_kwargs = {
            "date": {"required": False},
        }

    def get_base_payment_id(self, instance):
        """Get the ID of the base payment associated with the given transaction
        instance.

        This method retrieves the ID of the most recent base payment associated
        with the transaction. It filters the transaction payments based on the
        payment type (BASE_TRANSACTION) and returns the ID of the last payment
        in the filtered queryset.

        Parameters:
        - instance: The transaction instance.

        Returns:
        - int or None: The ID of the base payment, or None if no base payment
            is found.
        """
        base_payment = (
            instance.transaction_payments.filter(payment_type=BASE_TRANSACTION)
            .only("id")
            .last()
        )
        if base_payment:
            return base_payment.idencode
        return None

    def create_premium(self, premiums, transaction, node):
        """Function for create transaction premium."""
        for premium in premiums:
            Payment.objects.get_or_create(
                premium=premium["premium"],
                amount=premium["amount"],
                selected_option=premium.get("selected_option"),
                transaction=transaction,
            )

    @staticmethod
    def check_for_duplicate(validated_data):
        """Function for check duplicate external transaction exists."""
        try:
            transaction = ExternalTransaction.objects.get(
                type=validated_data["type"],
                price=validated_data["price"],
                currency=validated_data["currency"],
                date=validated_data["created_on"],
                verification_method=validated_data["verification_method"],
                client_type=validated_data["client_type"],
            )
            transaction.is_created = False
        except Exception:
            transaction = []
        return transaction

    @staticmethod
    def get_related_loss_trans(date, node, batches):
        """Function for get related loss transaction details of particular
        batches, date and node."""
        if not batches:
            return None
        internal_trans = trans_model.InternalTransaction.objects.filter(
            date=date,
            source_batches=batches[0]["batch"],
            type=trans_constants.INTERNAL_TRANS_TYPE_LOSS,
            node=node,
        ).first()
        return internal_trans

    @staticmethod
    def get_source_batches(batches):
        """Product data of source batches."""
        data = []
        for batch_data in batches:
            product_data = prods_serializers.ProductSerializer(
                batch_data["batch"].product
            ).data
            source_batch = trans_model.SourceBatch.objects.filter(
                batch=batch_data["batch"]
            ).first()
            if not source_batch:
                continue
            product_data["id"] = batch_data["batch"].idencode
            product_data["quantity"] = source_batch.quantity
            product_data["number"] = batch_data["batch"].number
            product_data["unit"] = batch_data["batch"].unit
            data.append(product_data)
        return data

    def validate(self, attrs):
        """Function for validate balance of batches."""
        if not attrs["batches"]:
            raise serializers.ValidationError("batch details are required")
        for batch_data in attrs["batches"]:
            if batch_data["batch"].current_quantity < batch_data["quantity"]:
                raise comm_exe.PaymentRequired()
        card = attrs.get("card")
        if isinstance(card, str):
            node = attrs["node"]
            cards = node.cards.filter(card_id=card)
            if not cards.exists():
                raise serializers.ValidationError(
                    "Invalid Card ID. Transaction not authorized"
                )
            attrs["card"] = cards.first()
        return attrs

    def create(self, validated_data):
        """Overriding the create method.

        Function for create external transaction and if lose is true
        then create internal transaction with type loss.
        """
        # node is the login user node id get from api header.
        node = self.context["view"].kwargs["node"]
        batches = validated_data["batches"]
        premiums = validated_data.pop("premium_paid")
        is_bal_loss = validated_data.pop("is_bal_loss", False)
        validated_data["date"] = validated_data["created_on"]
        transaction = self.check_for_duplicate(validated_data)
        if transaction:
            """Append source_batches details to response using the batches from
            the input.

            otherwise we got merged batch details as the source_batches
            """
            transaction.source_batch = self.get_source_batches(batches)
            transaction.loss_transaction = self.get_related_loss_trans(
                validated_data["created_on"], node, batches
            )
            return transaction
        transaction = super(AppSentTransactionSerializer, self).create(
            validated_data
        )
        transaction.created_on = validated_data["created_on"]
        transaction.save()
        transaction.source_batch = self.get_source_batches(batches)
        self.create_premium(premiums, transaction, node)
        if is_bal_loss:
            transaction.loss_transaction = self.create_balance_loss(
                batches, validated_data["date"]
            )
        return transaction

    def create_balance_loss(self, batches, date):
        """Function for creating internal transaction with loss type.

        The internal transaction batch quantity will be the remaining
        quantity of the batch.
        """
        for batch_data in batches:
            # re-fetching the batch to get the updated current quantity
            batch = Batch.objects.get(id=batch_data["batch"].id)
            if batch.current_quantity <= 0:
                batches.remove(batch_data)
                continue

            batch_data["quantity"] = batch.current_quantity
            batch_data["batch"] = batch
        if not batches:
            return None
        int_tran_serializer = (
            internal_serializers.InternalTransactionSerializer(
                data={
                    "type": trans_constants.INTERNAL_TRANS_TYPE_LOSS,
                    "source_batches": batches,
                    "client_type": trans_constants.CLIENT_APP,
                    "date": date,
                },
                context=self.context,
            )
        )
        if not int_tran_serializer.is_valid():
            raise serializers.ValidationError(int_tran_serializer.errors)
        transaction = int_tran_serializer.save()
        return transaction


class AppTransactionListSerializer(serializers.ModelSerializer):
    """Serializer for list sent transaction details.

    include both internal and external transactions.
    """

    id = custom_fields.IdencodeField(read_only=True)
    date = serializers.DateTimeField(required=False)
    price = serializers.SerializerMethodField("get_price", default=None)
    currency = serializers.SerializerMethodField("get_currency", default=None)
    source = serializers.SerializerMethodField("get_source", default=None)
    destination = serializers.SerializerMethodField(
        "get_destination", default=None
    )
    source_batches = serializers.SerializerMethodField(
        "get_source_products", default=None
    )
    destination_batches = serializers.SerializerMethodField(
        "get_destination_products", default=None
    )
    created_on = custom_fields.UnixTimeField()
    updated_on = custom_fields.UnixTimeField()
    premiums = IssuedPremiumSerializer(
        allow_null=True, many=True, source="premium_paid"
    )
    product_price = serializers.SerializerMethodField(
        "get_product_price", default=None
    )
    verification_latitude = serializers.SerializerMethodField(
        "get_verification_lati", default=None
    )
    verification_longitude = serializers.SerializerMethodField(
        "get_verification_longi", default=None
    )
    quantity = serializers.SerializerMethodField(read_only=True, default=None)
    source_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True, default=None
    )
    destination_quantity = custom_fields.RoundingDecimalField(
        max_digits=25, decimal_places=3, read_only=True, default=None
    )
    logged_time = serializers.DateTimeField(
        source="created_on", read_only=True, default=None
    )
    claims = custom_fields.ManyToManyIdencodeField(
        serializer=product_claims.BatchClaimSerializer,
        source="get_claims",
        read_only=True,
        default=None,
    )
    card_details = NodeCardSerializer(source="card", read_only=True)
    mode = serializers.SerializerMethodField("get_mode", default=None)
    category = serializers.SerializerMethodField("get_category", default=None)
    card = custom_fields.IdencodeField()
    base_payment_id = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = (
            "id",
            "date",
            "price",
            "currency",
            "source",
            "destination",
            "number",
            "source_batches",
            "destination_batches",
            "created_on",
            "updated_on",
            "premiums",
            "invoice",
            "card",
            "quality_correction",
            "verification_method",
            "client_type",
            "product_price",
            "verification_latitude",
            "verification_longitude",
            "source_quantity",
            "destination_quantity",
            "logged_time",
            "comment",
            "claims",
            "blockchain_address",
            "mode",
            "quantity",
            "category",
            "extra_fields",
            "base_payment_id",
            "card_details",
            "invoice_number"
        )

    def get_base_payment_id(self, instance):
        """Get the ID of the base payment associated with the given transaction
        instance.

        This method retrieves the ID of the most recent base payment associated
        with the transaction. It filters the transaction payments based on the
        payment type (BASE_TRANSACTION) and returns the ID of the last payment
        in the filtered queryset.

        Parameters:
        - instance: The transaction instance.

        Returns:
        - int or None: The ID of the base payment, or None if no base payment
            is found.
        """
        base_payment = (
            instance.transaction_payments.filter(payment_type=BASE_TRANSACTION)
            .only("id")
            .last()
        )
        if base_payment:
            return base_payment.idencode
        return None

    def get_price(self, instance):
        """To perform function get_price."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            price = instance.externaltransaction.price
            return price

    def get_quantity(self, instance):
        """To perform function get_quantity."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            return instance.externaltransaction.quantity
        return instance.source_quantity

    def get_currency(self, instance):
        """To perform function get_currency."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            currency = instance.externaltransaction.currency
            return currency

    def get_source(self, instance):
        """To perform function get_source."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            source = NodeBasicSerializer(
                instance.externaltransaction.source
            ).data
            return source

    def get_destination(self, instance):
        """To perform function get_destination."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            destination = NodeBasicSerializer(
                instance.externaltransaction.destination
            ).data
            return destination

    def get_source_products(self, instance):
        """Product data of source batches."""
        data = []
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            source_batches = (
                instance.externaltransaction.source_batch_objects.all()
            )
        elif (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_INTERNAL
        ):
            source_batches = (
                instance.internaltransaction.source_batch_objects.all()
            )
        for source_batch in source_batches:
            product_data = prods_serializers.ProductSerializer(
                source_batch.batch.product
            ).data
            product_data["product_id"] = product_data["id"]
            product_data["id"] = source_batch.batch.idencode
            product_data["quantity"] = source_batch.quantity
            product_data["number"] = source_batch.batch.number
            product_data["unit"] = source_batch.batch.unit
            data.append(product_data)

        return data

    def get_destination_products(self, instance):
        """Product data of destination batches."""
        data = []
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            result_batches = instance.externaltransaction.result_batches.all()
        elif (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_INTERNAL
        ):
            result_batches = instance.internaltransaction.result_batches.all()
        for result_batch in result_batches:
            product_data = prods_serializers.ProductSerializer(
                result_batch.product
            ).data
            product_data["product_id"] = product_data["id"]
            product_data["id"] = result_batch.idencode
            product_data["quantity"] = result_batch.initial_quantity
            product_data["number"] = result_batch.number
            product_data["unit"] = result_batch.unit
            product_data["current_quantity"] = result_batch.current_quantity
            data.append(product_data)
        return data

    def get_product_price(self, instance):
        """To perform function get_product_price."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            product_price = instance.externaltransaction.product_price
            return product_price

    def get_verification_lati(self, instance):
        """To perform function get_verification_lati."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            verification_lati = (
                instance.externaltransaction.verification_latitude
            )
            return verification_lati

    def get_verification_longi(self, instance):
        """To perform function get_verification_longi."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            verification_longi = (
                instance.externaltransaction.verification_longitude
            )
            return verification_longi

    def get_mode(self, instance):
        """To perform function get_mode."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_INTERNAL
        ):
            mode = instance.internaltransaction.mode
            return mode

    def get_category(self, instance):
        """Function for get the type of app transaction."""
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            if (
                instance.externaltransaction.type
                == trans_constants.EXTERNAL_TRANS_TYPE_OUTGOING
            ):
                category = project_const.APP_TRANS_TYPE_OUTGOING
            elif (
                instance.externaltransaction.type
                == trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
            ):
                category = project_const.APP_TRANS_TYPE_INCOMING
        elif (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_INTERNAL
        ):
            category = project_const.APP_TRANS_TYPE_LOSS
        return category

    def to_representation(self, instance):
        """Quantity to be shown in the interface will different for source and
        destination companies."""
        data = super(AppTransactionListSerializer, self).to_representation(
            instance
        )
        try:
            node = self.context["view"].kwargs["node"]
        except Exception:
            node = self.context["node"]
        if (
            instance.transaction_type
            == trans_constants.TRANSACTION_TYPE_EXTERNAL
        ):
            if node == instance.externaltransaction.source:
                data["quantity"] = instance.externaltransaction.source_quantity
            elif node == instance.externaltransaction.destination:
                data[
                    "quantity"
                ] = instance.externaltransaction.destination_quantity
            common_lib._pop_out_from_dictionary(
                data, ["source_quantity", "destination_quantity"]
            )
        return data
