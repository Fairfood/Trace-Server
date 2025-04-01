"""Tests of the app products."""
from django.conf import settings
from django.urls import reverse
from mixer.backend.django import mixer
from rest_framework import status
from v2.products.models import Batch
from v2.products.models import Product
from v2.products.tests.integration.base import ProductsBaseTestCase


# Create your tests here.


class ProductTestCase(ProductsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.product = mixer.blend(Product, supply_chain=self.supply_chain)
        self.create_external_transaction()
        self.batch = mixer.blend(
            Batch,
            product=self.product,
            node=self.company,
            source_transaction=self.transaction,
        )

    def test_product(self):
        """Test for list and create Products based on a supply chain."""
        product_url = reverse("product")
        data = {
            "name": self.faker.name(),
            "supply_chain": self.supply_chain.idencode,
        }
        response = self.client.post(
            product_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(product_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bulk_product(self):
        """Test for create bulk Products based on a supply chain."""
        bulk_product_url = reverse("bulk-product")
        data = {
            "supply_chain": self.supply_chain.idencode,
            "products": [
                "New Product 3",
                "New Product 8",
                "new product 10",
                "New Product 9",
                "New Product 7",
            ],
        }
        response = self.client.post(
            bulk_product_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_batch(self):
        """Test for list batches of a node."""
        batch_url = reverse("batch")
        response = self.client.get(batch_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_batch_details(self):
        """Test for get batch details."""
        batch_url = reverse("batch-details", kwargs={"pk": self.batch.id})
        response = self.client.get(batch_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_batch_trace(self):
        """Test for get batch trace."""
        batch_url = reverse("batch-trace", kwargs={"pk": self.batch.id})
        self.totp_secret = settings.CI_TOTP_SECRET
        response = self.client.get(batch_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_archived_batches(self):
        """Test for get archived batches."""
        self.create_archived_batch()
        batch_url = reverse("batch")
        data = {
            "archived": "true",
        }
        response = self.client.get(batch_url, data=data, 
                                   format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def create_archived_batch(self):
        """Create archived batch."""
        mixer.blend(
            Batch,
            product=self.product,
            node=self.company,
            source_transaction=self.transaction,
            archived=True,
        )

    def test_archive_batch(self):
        toggl_archive_url = reverse("toggle-archive")
        data = {
            "is_excluded": True,
        }
        response = self.client.post(
            toggl_archive_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)