"""Tests of the app transactions."""
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from mixer.backend.django import mixer
from rest_framework import status
from v2.products.models import Batch
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Company
from v2.supply_chains.models import Connection
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import NodeSupplyChain
from v2.transactions.models import InternalTransaction
from v2.transactions.tests.integration.base import TransactionBaseTestCase

# Create your tests here.

PA = "/v2/bulk_templates/tests/Bulk_upload_template_10-05-2022_123441.xlsx"


class TransactionTestCase(TransactionBaseTestCase):
    def setUp(self):
        super().setUp()
        file_name = "Bulk_upload_template_10-05-2022_123441.xlsx"
        self.file_path = (
            settings.BASE_DIR + "/v2/bulk_templates/tests/" + file_name
        )

    def test_external_transaction(self):
        """Test for list and create external transaction."""
        destination = mixer.blend(Company, type=NODE_TYPE_COMPANY)
        mixer.blend(
            NodeSupplyChain,
            node=destination,
            supply_chain=self.supply_chain,
            primary_operation=self.operation,
        )
        batch = mixer.blend(
            Batch,
            product=self.product,
            node=self.company,
            current_quantity=500,
        )
        mixer.blend(
            Connection,
            buyer=destination,
            supplier=self.company,
            supply_chain=self.supply_chain,
        )
        node = self.company.get_connections(supply_chain=self.supply_chain)[0]
        external_url = reverse("external")
        data = {
            "date": timezone.now(),
            "node": node.id,
            "type": 1,
            "product": self.product.idencode,
            "quantity": 395.0,
            "unit": 1,
            "comment": "New external transaction",
            "batches": [
                {"batch": batch.idencode, "quantity": 1},
            ],
        }
        response = self.client.post(
            external_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(external_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_external_bulk_transaction(self):
    #     """
    #     Test for list and create bulk external transaction
    #     """
    #     external_bulk_url = reverse("external-bulk")
    #     data = {
    #         "date": "1992-05-10",
    #         "node": "pX4Wp",
    #         "type": 1,
    #         "product": "0eaM0",
    #         "quantity": 395.0,
    #         "unit": 1,
    #         "currency": "",
    #         "comment": "New external transaction",
    #         "batches": [{
    #             "batch": 'yD1jW',
    #             "quantity": 1
    #         }]
    #     }
    #     response = self.client.post(
    #         external_bulk_url, data, format='json', **self.header)
    #     self.assertEqual(response.status_code,
    #                      status.HTTP_201_CREATED)

    def test_external_transaction_details(self):
        """Test for external transaction details."""
        self.create_external_transaction()
        external_details_url = reverse(
            "external-details", kwargs={"pk": self.transaction.id}
        )
        response = self.client.get(
            external_details_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_external_transaction_reject(self):
        """Test for external transaction reject."""
        self.create_external_transaction()
        external_reject_url = reverse(
            "external-reject", kwargs={"pk": self.transaction.id}
        )
        data = {"comment": "test comment"}
        response = self.client.post(
            external_reject_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_bulk_transaction_template(self):
        """Test to get or create bulk transaction template."""
        bulk_template_url = reverse("bulk-transaction-template")
        with open(self.file_path, "rb") as fp:
            data = {"file": fp}
            response = self.client.post(
                bulk_template_url, data, **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def create_internal_transaction(self):
        internal_url = reverse("internal")
        farmer = mixer.blend(Farmer, type=NODE_TYPE_FARM, creator=self.user,
                             updater=self.user)
        batch = mixer.blend(
            Batch, product=self.product, node=farmer, current_quantity=500
        )
        data = {
            "type": 1,
            "date": timezone.now(),
            "destination_batches": [
                {
                    "product": (self.product.idencode),
                    "quantity": 500,
                    "unit": 1,
                },
            ],
            "source_batches": [
                {
                    "batch": batch.idencode,
                    "quantity": 1,
                },
            ],
        }

        return self.client.post(
            internal_url, data, format="json", **self.headers
        )

    def test_internal_transaction(self):
        """Test for list and create internal transaction."""
        internal_url = reverse("internal")
        response = self.create_internal_transaction()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(internal_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_internal_transaction_details(self):
        """Test for external transaction details."""
        self.create_internal_transaction()
        internal_txn = InternalTransaction.objects.first()
        internal_details_url = reverse(
            "internal-details", kwargs={"pk": internal_txn.id}
        )
        response = self.client.get(
            internal_details_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
