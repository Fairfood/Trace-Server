"""Tests of the app supply chain."""
from django.conf import settings
from django.urls import reverse
from mixer.backend.django import mixer
from rest_framework import status
from v2.dashboard.models import NodeStats
from v2.supply_chains.models import BulkExcelUploads
from v2.supply_chains.models import Label
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.tests.integration.base import SupplyChainBaseTestCase

# Create your tests here.

PA = "/v2/bulk_templates/tests/Bulk_upload_template_10-05-2022_123441.xlsx"


class SupplyChainTestCase(SupplyChainBaseTestCase):
    def setUp(self):
        super().setUp()
        self.company.create_or_update_graph_node()
        mixer.blend(NodeStats, node=self.company)
        self.file_path = settings.BASE_DIR + PA

    def test_farmer_bulk(self):
        """Test for farmer bulk registration."""
        nsc = NodeSupplyChain.objects.filter(
            primary_operation__isnull=False
        ).first()
        file = BulkExcelUploads.objects.filter(node=self.company).last()
        if file:
            farmer_bulk_url = reverse("farmer-bulk")
            data = {
                "supply_chain": nsc.supply_chain.idencode,
                "supplier_for": [self.company.idencode],
                "file": file.idencode,
                "farmers": [
                    {
                        "city": "city 1",
                        "country": "Ireland",
                        "email": "aaa@aaa.com",
                        "first_name": "anjuna",
                        "primary_operation": nsc.primary_operation.idencode,
                        "product_id": (
                            nsc.supply_chain.products.first().idencode
                        ),
                        "price_per_unit": 10,
                        "quantity": 100,
                        "invoice_number": "invoice_number",
                    },
                    {
                        "email": "anjuna@cied.in",
                        "first_name": "My New",
                        "last_name": "Name",
                        "primary_operation": nsc.primary_operation.idencode,
                        "product_id": (
                            nsc.supply_chain.products.first().idencode
                        ),
                        "price_per_unit": 10,
                        "quantity": 100,
                        "invoice_number": "invoice_number",
                    },
                ],
            }
            response = self.client.post(
                farmer_bulk_url, data, format="json", **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invite_company(self):
        """Test for invite company."""
        invite_company_url = reverse("invite-company")
        data = {
            "supply_chain": self.supply_chain.idencode,
            "message": "Welcome to Fairfood",
            "buyer_for": [],
            "relation": 1,
            "send_email": "false",
            "name": self.faker.name(),
            "primary_operation": self.operation.idencode,
            "incharge": {
                "first_name": self.faker.first_name(),
                "last_name": self.faker.last_name(),
                "email": self.faker.email(),
            },
        }
        response = self.client.post(
            invite_company_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invite_farmer(self):
        """Test for invite farmer."""
        invite_farmer_url = reverse("invite-farmer")
        data = {
            "supply_chain": self.supply_chain.idencode,
            "relation": 2,
            "first_name": self.faker.first_name(),
            "last_name": self.faker.last_name(),
            "primary_operation": self.operation.idencode,
            "identification_no": self.faker.random_number(),
            "street": self.faker.street_name(),
            "city": self.faker.city(),
        }
        response = self.client.post(
            invite_farmer_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_resend_invitation(self):
        """Test for resend invitation."""
        resend_invitation_url = reverse("resend-invitation")
        data = {
            "supply_chain": self.supply_chain.idencode,
            "node": self.company.id,
        }
        response = self.client.post(
            resend_invitation_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # def test_farmer_bulk(self):
    #     """
    #     Test for retrieve map connections.
    #     """
    #     nsc = NodeSupplyChain.objects.filter(
    #         primary_operation__isnull=False
    #     ).first()
    #     map_connections_url = reverse(
    #         "map-connections", kwargs={"pk": nsc.node.id}
    #     )
    #     response = self.client.get(
    #         map_connections_url,
    #         {"supply_chain": nsc.supply_chain.idencode},
    #         format="json",
    #         **self.header,
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_table_connections(self):
        """Test for retrieve table connections."""
        map_connections_url = reverse(
            "table-connections", kwargs={"pk": self.company.id}
        )
        response = self.client.get(
            map_connections_url,
            {"supply_chain": self.supply_chain.idencode},
            format="json",
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tag_connection(self):
        """Test for update tag connection."""
        tag_connection_url = reverse(
            "tag-connection", kwargs={"pk": self.company.id}
        )
        data = {"supply_chain": self.supply_chain.idencode}
        response = self.client.patch(
            tag_connection_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_connection_search(self):
        """Test for search connection."""
        search_connection_url = reverse(
            "connection-search", kwargs={"pk": self.company.id}
        )
        response = self.client.get(
            search_connection_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_suppliers(self):
        """Test for get suppliers."""
        suppliers_url = reverse("suppliers")
        response = self.client.get(
            suppliers_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_buyers(self):
        """Test for get buyers."""
        buyers_url = reverse("buyers")
        response = self.client.get(buyers_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_label(self):
        """Test for create and get label."""
        label_url = reverse("label")
        data = {
            "name": self.faker.name(),
            "supply_chains": [self.supply_chain.idencode],
        }
        response = self.client.post(
            label_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(label_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_label(self):
        """Test for retrieve and delete label."""
        label = Label.objects.create(name="test label")
        update_label_url = reverse("labels", kwargs={"pk": label.id})
        data = {
            "name": self.faker.name(),
            "supply_chains": [self.supply_chain.idencode],
        }
        response = self.client.patch(
            update_label_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(
            update_label_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_connection_label(self):
        """Test for update connection label."""
        conn = self.company.supplier_connections.last()
        label = Label.objects.first()
        if label:
            update_label_url = reverse(
                "connection-label", kwargs={"pk": conn.id}
            )

            data = {
                "labels": [
                    label.idencode,
                ]
            }
            response = self.client.patch(
                update_label_url, data, format="json", **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bulk_farmer_template(self):
        """Test for get and verify bulk farmer template."""
        farmer_template_url = reverse("farmer-template")

        with open(self.file_path, "rb") as fp:
            data = {"file": fp}
            response = self.client.post(
                farmer_template_url, data, **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_node_supply_chain(self):
        """Test for delete node supply chain."""
        self.change_to_admin_user()
        node_supply_chain = self.company.nodesupplychain_set.last()
        node_supply_chain_url = reverse(
            "node-supply_chain", kwargs={"pk": node_supply_chain.id}
        )
        response = self.client.delete(
            node_supply_chain_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_supply_chain_active(self):
        """Test for make supply chain active."""
        supply_chain_active_url = reverse(
            "supply_chain-active", kwargs={"pk": self.supply_chain.id}
        )
        response = self.client.post(
            supply_chain_active_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
