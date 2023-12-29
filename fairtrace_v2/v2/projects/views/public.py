"""This file manage public SMS apis."""
from common import library
from common.constants import LANGUAGE_DUTCH
from common.constants import LANGUAGE_ENG
from common.constants import LANGUAGE_INDONESIAN
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from v2.projects.constants import BAL_SMS_MSG
from v2.projects.constants import BASE_PREMIUM
from v2.projects.constants import CARD_STATUS_ACTIVE
from v2.projects.constants import TRANSACTION_PREMIUM
from v2.projects.models import NodeCard
from v2.projects.models import Payment
from v2.projects.serializers import public as pub_serials
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import SourceBatch


class SMSBalanceAPIView(generics.CreateAPIView):
    """View to test APIs."""

    serializer_class = pub_serials.SMSBalanceWebhookSerializer


class WhatsAppWebHookView(APIView):
    """View for handling incoming WhatsApp webhook requests."""

    def get(self, request, **kwargs):
        """Handles the POST request from the webhook endpoint.

        Parameters:
        - request (HttpRequest): The HTTP request object.
        - **kwargs: Additional keyword arguments.

        Returns:
        - Response: The HTTP response containing the generated SMS content.
        """
        payload = self._get_payload()
        lan = self._get_language(**kwargs)
        node = self._fetch_node(payload)
        message = self._generate_sms_content(node, lan)
        return Response(message)

    def _fetch_node(self, fairid):
        """Function to process fair-id and get farmer.

        Fair-id usually starts with FF but we have removed FF in DB. It
        is always caps.
        """
        card = NodeCard.objects.filter(
            fairid=fairid, status=CARD_STATUS_ACTIVE
        ).first()
        if not card:
            raise ValidationError("Invalid FairID")

        return card.node

    def _get_payload(self):
        """Function to get payload."""
        payload = self.request.query_params.get("fair_id")
        if not payload:
            raise ValidationError(detail="fair_id is required.")

        # Validating the payload.
        payload = payload.replace(" ", "").upper()
        if payload.startswith("FF"):
            payload = payload.replace("FF", "", 1)
        return payload

    @staticmethod
    def _get_language(**kwargs):
        """Function to get language."""
        lan = kwargs.get("lan")
        lan_map = {
            "en": LANGUAGE_ENG,
            "nl": LANGUAGE_DUTCH,
            "id": LANGUAGE_INDONESIAN,
        }
        return lan_map.get(lan, LANGUAGE_ENG)

    def _generate_sms_content(self, node, language):
        """Function to generate SMS content."""
        transactions = ExternalTransaction.objects.filter(
            source=node
        ).order_by("created_on")
        try:
            if not transactions:
                return BAL_SMS_MSG[language]["404_message"]

            message = BAL_SMS_MSG[language]["message"].format(
                **self._get_sales_sms_data(transactions)
            )
        except KeyError:
            raise ValidationError(
                "Content for this language is not " "available."
            )
        print("sms message: ", message)
        return message

    def _get_sales_sms_data(self, sales):
        """Function to create sale data."""
        payments = Payment.objects.filter(
            transaction__externaltransaction__in=list(sales),
            payment_type__in=[BASE_PREMIUM, TRANSACTION_PREMIUM],
        )
        total_premium = library.query_sum(payments, "amount")
        total_price = library.query_sum(sales, "price")
        source_batches = SourceBatch.objects.filter(
            transaction__externaltransaction__in=sales
        )
        total_quantity = library.query_sum(source_batches, "quantity")
        avg_premium = 0
        if total_quantity:
            avg_premium = round((total_premium / total_quantity), 2)
        data = {
            "name": library.get_acronym(sales.first().source.full_name),
            "start_date": str(sales.first().created_on.date()),
            "total_quantity": f"{total_quantity} KG",
            "total_payment": f"{total_price + total_premium} "
            f"{sales.last().currency}",
            "total_premium": f"{total_premium} {sales.last().currency}",
            "avg_premium": f"{avg_premium} {sales.last().currency}",
        }
        data.update(self._get_last_sale_sms_data(sales.last()))
        return data

    @staticmethod
    def _get_last_sale_sms_data(transaction):
        """Function to create last sale SMS data."""
        payments = Payment.objects.filter(transaction=transaction.id)
        last_premium = library.query_sum(payments, "amount")
        data = {
            "last_sale_date": str(transaction.created_on.date()),
            "last_quantity": f"{float(transaction.source_quantity)} KG",
            "last_premium": f"{last_premium} {transaction.currency}",
            "last_total": (
                f"{last_premium + transaction.price}"
                f" {transaction.currency}"
            ),
        }
        return data
