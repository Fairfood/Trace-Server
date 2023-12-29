"""Serializer used in the public apis."""
from common import constants as com_consts
from common import library
from common import vendors
from rest_framework import serializers
from v2.projects import constants as proj_consts
from v2.projects.models import NodeCard
from v2.projects.models import Payment
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import SourceBatch


class SMSBalanceWebhookSerializer(serializers.Serializer):
    """Serializer used for SMS passbook web-hook api.

    This serializer is triggered when the user send an SMS
    to check the balance of the farmer with FairID.
    Fields:
        payload(char): content of the SMS
        originator(char): sender phone number
        recipient(char): Trace number to which sms was initiated.
    """

    payload = serializers.CharField(write_only=True)
    originator = serializers.CharField(write_only=True)
    recipient = serializers.CharField(write_only=True)

    def validate_payload(self, value):
        """To validate payload."""
        value = value.replace(" ", "").upper()
        if value.startswith("FF"):
            value = value.replace("FF", "", 1)
        return value

    def validate_originator(self, value):
        """To validate originator."""
        value = value.replace(" ", "")
        if not (value.startswith("+")):
            value = f"+{value}"
        return value

    def validate_recipient(self, value):
        """To validate recipient."""
        value = value.replace(" ", "")
        if not (value.startswith("+")):
            value = f"+{value}"
        return value

    def create(self, validated_data):
        """Overriding the create method recipient."""
        node = self._fetch_node(validated_data["payload"])
        language = self._get_sms_language(validated_data["recipient"])
        vendors.send_farmer_sms(
            validated_data["recipient"],
            self._generate_sms_content(node, language),
            validated_data["originator"],
        )
        return {"success": True}

    @staticmethod
    def _get_sms_language(recipient: str) -> int:
        """To get sms content language from the sender number."""
        for key, value in proj_consts.BAL_SMS_MSG.items():
            if value["sender"] == recipient:
                return key
        return com_consts.LANGUAGE_ENG

    def _fetch_node(self, fairid: str):
        """Function to process fair-id and get farmer.

        Fair-id usually starts with FF but we have removed FF in DB. It
        is always caps.
        """
        try:
            node = NodeCard.objects.get(
                fairid=fairid, status=proj_consts.CARD_STATUS_ACTIVE
            ).node
        except NodeCard.DoesNotExist:
            raise serializers.ValidationError("Invalid FairID")
        return node

    def _generate_sms_content(self, node, language):
        """To generate SMS content."""
        sales = ExternalTransaction.objects.filter(source=node).order_by(
            "created_on"
        )
        if not sales:
            return proj_consts.BAL_SMS_MSG[language]["404_message"]

        message = proj_consts.BAL_SMS_MSG[language]["message"].format(
            **self._get_sales_sms_data(sales)
        )
        print("sms message: ", message)
        return message

    def _get_sales_sms_data(self, sales):
        """Function to create sale data."""
        total_premium = library._query_sum(
            Payment.objects.filter(
                transaction__externaltransaction__in=list(sales)
            ),
            "amount",
        )
        total_price = library._query_sum(sales, "price")
        total_quantity = library._query_sum(
            SourceBatch.objects.filter(
                transaction__externaltransaction__in=sales
            ),
            "quantity",
        )
        avg_premium = 0
        if total_quantity:
            avg_premium = round((total_premium / total_quantity), 2)
        data = {
            "name": library.get_acronym(sales.first().source.full_name),
            "start_date": str(sales.first().created_on.date()),
            "total_quantity": f"{total_quantity} KG",
            "total_payment": (
                f"{total_price + total_premium} {sales.last().currency}"
            ),
            "total_premium": f"{total_premium} {sales.last().currency}",
            "avg_premium": f"{avg_premium} {sales.last().currency}",
        }
        data.update(self._get_last_sale_sms_data(sales.last()))
        return data

    @staticmethod
    def _get_last_sale_sms_data(txn):
        """Function to create last sale SMS data."""
        last_premium = library._query_sum(
            Payment.objects.filter(transaction=txn.id), "amount"
        )
        data = {
            "last_sale_date": str(txn.created_on.date()),
            "last_quantity": f"{float(txn.source_quantity)} KG",
            "last_premium": f"{last_premium} {txn.currency}",
            "last_total": f"{last_premium + txn.price} {txn.currency}",
        }
        return data
