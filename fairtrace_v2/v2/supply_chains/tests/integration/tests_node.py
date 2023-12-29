"""Tests of the app supply chain."""
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from v2.supply_chains import constants
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import NodeDocument
from v2.supply_chains.models import Operation
from v2.supply_chains.tests.integration.base import SupplyChainBaseTestCase

# Create your tests here.

PA = "/v2/bulk_templates/tests/Bulk_upload_template_10-05-2022_123441.xlsx"


class NodeTestCase(SupplyChainBaseTestCase):
    def setUp(self):
        super().setUp()
        self.change_to_admin_user()
        self.node_doc = NodeDocument.objects.create(node=self.company)
        self.file_path = settings.BASE_DIR + PA

    def test_farmer(self):
        """Test for farmer registration."""
        farmer_url = reverse("farmer")
        Operation.objects.create(name="Brand", node_type=1)
        operation = Operation.objects.first()
        data = {
            "first_name": "john",
            "last_name": "kk",
            "family_members": 5,
            "farm_area": "kozhikode",
            "primary_operation": operation.idencode,
            "managers": self.company.idencode,
        }

        response = self.client.post(
            farmer_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_connection(self):
        """Test for get connection details."""
        connection_url = reverse("connections")
        response = self.client.get(
            connection_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_supply_chain_list(self):
        """Test for get supply chain."""
        supply_chain_url = reverse("supply-chain")
        response = self.client.get(
            supply_chain_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_farmer_details(self):
        """Test to get farmer details."""
        node_member = self.company.nodemembers.last()
        farmer = Farmer.objects.create(
            first_name=self.faker.first_name(),
            last_name=self.faker.last_name(),
            creator=self.user, updater=self.user
        )
        farmer.managers.add(node_member.node)
        farmer_details_url = reverse(
            "farmer-details", kwargs={"pk": farmer.id}
        )
        response = self.client.get(farmer_details_url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        farmer_data = {"farm_area": self.faker.street_name()}
        resp = self.client.patch(
            farmer_details_url, farmer_data, format="json", **self.headers
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        farmer.delete()

    # TODO: Need to rewrite logic
    # def test_company_details(self):
    #     """Test to get company details."""
    #     node = self.node.supplier_connections.last()
    #     if node:
    #         node = node.supplier
    #     else:
    #         node = self.node.buyer_connections.last()
    #         if node:
    #             node = node.buyer
    #     company_details_url = reverse(
    #         "company-details", kwargs={"pk": node.id}
    #     )
    #     response = self.client.get(company_details_url, **self.header)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    #     company_data = {"name": "vc", "role": constants.COMPANY_ROLE_ACTOR}
    #     response = self.client.patch(
    #         company_details_url, company_data, format="json", **self.header
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_node_member(self):
        """Test for node member registration."""
        member_url = reverse("node-member")
        data = {
            "first_name": self.faker.first_name(),
            "last_name": self.faker.last_name(),
            "email": self.faker.email(),
            "active": "true",
            "email_verified": "true",
            "type": constants.NODE_MEMBER_TYPE_VIEWER,
        }
        response = self.client.post(
            member_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        resp = self.client.get(member_url, **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_resend_node_member(self):
        """Test for resend invite to node member."""
        member = self.company.nodemembers.last()
        resend_url = reverse("resend-node-member", kwargs={"pk": member.id})
        data = {
            "email": self.email,
        }
        response = self.client.post(
            resend_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_node_document(self):
        """Test to create node documents."""
        node_doc_url = reverse("node-document")
        with open(self.file_path, "rb") as fp:
            data = {"name": self.faker.name(), "file": fp}
            response = self.client.post(node_doc_url, data, **self.headers)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_remove_node_document(self):
        """Test to destroy node document."""
        document_id = self.node_doc.id
        update_node_document_url = reverse(
            "remove-node-document", kwargs={"pk": document_id}
        )
        response = self.client.delete(
            update_node_document_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_managed_farmers(self):
        """Test to list managed farmers."""
        self.test_farmer()
        managed_farmer_url = reverse("managed-farmers")
        response = self.client.get(
            managed_farmer_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
