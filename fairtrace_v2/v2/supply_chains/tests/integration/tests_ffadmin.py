"""Tests of ffadmin supply chain."""
from django.conf import settings
from django.urls import reverse
from mixer.backend.django import mixer
from rest_framework import status
from v2.accounts.models import Person
from v2.dashboard.models import NodeStats
from v2.products.models import Product
from v2.supply_chains.constants import NODE_INVITED_BY_FFADMIN
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.models import AdminInvitation
from v2.supply_chains.models import Company
from v2.supply_chains.models import Connection
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.models import Operation
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.models import Verifier
from v2.supply_chains.tests.integration.base import SupplyChainBaseTestCase

# Create your tests here.

FP = "/v2/bulk_templates/tests/Bulk_upload_template_10-05-2022_123441.xlsx"


class FFAdminTestCase(SupplyChainBaseTestCase):
    def setUp(self):
        super(FFAdminTestCase, self).setUp()
        self.change_to_admin_user()
        self.file_path = settings.BASE_DIR + FP

    def test_admin_supply_chain(self):
        """Test for get supply chain."""
        admin_supply_chain_url = reverse("admin-supplychain")
        response = self.client.get(
            admin_supply_chain_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_company(self):
        """Test for get company."""
        admin_company_url = reverse("admin-company")
        response = self.client.get(
            admin_company_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_company_details(self):
        """Test for get company."""
        admin_company_details_url = reverse(
            "admin-company-details", kwargs={"pk": self.company.id}
        )
        response = self.client.get(
            admin_company_details_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_company_invite(self):
        """Test for invite admin company."""
        admin_company_invite_url = reverse("admin-invite-company")
        data = {
            "supply_chains": [
                {
                    "supply_chain": self.supply_chain.idencode,
                    "primary_operation": self.operation.idencode,
                    "verifier": False,
                }
            ],
            "name": self.faker.name(),
            "date_joined": "2012-09-04 06:00:00.000000",
            "incharge": {
                "first_name": self.faker.first_name(),
                "last_name": self.faker.last_name(),
                "email": self.faker.email(),
            },
        }
        response = self.client.post(
            admin_company_invite_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_company_member(self):
        """Test for invite admin company member."""
        admin_company_member_url = reverse(
            "admin-company-member", kwargs={"pk": self.company.id}
        )
        data = {
            "first_name": self.faker.first_name(),
            "last_name": self.faker.last_name(),
            "type": 1,
            "email": self.faker.email(),
        }
        response = self.client.post(
            admin_company_member_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_member_details(self):
        """Test for get company member details."""
        node_mem = self.company.nodemembers.last()
        admin_company_details_url = reverse(
            "admin-member-details", kwargs={"pk": node_mem.id}
        )
        response = self.client.get(
            admin_company_details_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_nodemember_resend(self):
        """Test for Resend invite to node member."""
        node_mem = self.company.nodemembers.last()

        nodemember_resend_url = reverse(
            "admin-resend-nodemember", kwargs={"pk": node_mem.id}
        )
        response = self.client.post(
            nodemember_resend_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_company_activity(self):
        """Test for get company activity list."""
        nodemember_resend_url = reverse(
            "admin-company-activity", kwargs={"pk": self.company.id}
        )
        response = self.client.get(
            nodemember_resend_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_node_supply_chain(self):
        """Test to create supply chain in company."""
        supply_chain = SupplyChain.objects.create(name=self.faker.name())
        operation = mixer.blend(Operation, node_type=NODE_TYPE_COMPANY)
        NodeStats.objects.get_or_create(node=self.company)
        self.company.create_or_update_graph_node()
        node_supply_chain_url = reverse(
            "admin-node-supplychain", kwargs={"pk": self.company.id}
        )
        data = {
            "supply_chains": [
                {
                    "supply_chain": supply_chain.idencode,
                    "primary_operation": operation.idencode,
                    "verifier": False,
                }
            ],
        }
        response = self.client.post(
            node_supply_chain_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_node_supply_chain_list(self):
        """Test to list supply chain in company."""
        mixer.blend(NodeStats, node=self.company)
        self.company.create_or_update_graph_node()
        node_supply_chain_url = reverse(
            "admin-node-supplychain-list", kwargs={"pk": self.company.id}
        )
        response = self.client.get(
            node_supply_chain_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_supply_chain_save(self):
        """Test to list and create supply chain."""
        supply_chain_url = reverse("admin-supply-chain")
        data = {"name": self.faker.name()}
        response = self.client.post(
            supply_chain_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(
            supply_chain_url, format="json", **self.headers
        )
        # print("@@@@@@@@@@@@@@ response2", response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_supply_chain_update(self):
        """Test to retrieve supply chain details."""
        supply_chain_url = reverse(
            "admin-supply-chain-update", kwargs={"pk": self.supply_chain.id}
        )
        data = {"name": self.faker.name()}
        response = self.client.patch(
            supply_chain_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_invitation_resend(self):
        """Test to resend companies which is not joined."""
        node = mixer.blend(Company, type=NODE_TYPE_COMPANY)
        ns = mixer.blend(
            NodeSupplyChain,
            node=node,
            supply_chain=self.supply_chain,
            primary_operation=self.operation,
            invited_by=NODE_INVITED_BY_FFADMIN,
        )
        mixer.blend(
            Connection,
            buyer=self.company,
            supplier=node,
            supply_chain=self.supply_chain,
        )
        invite = mixer.blend(AdminInvitation, invitee=node)
        incharge = mixer.blend(Person, email=self.email)
        node.incharge = incharge
        node.save()
        invite.node_supply_chains.add(ns)
        supply_chain_url = reverse(
            "admin-invitation-resend", kwargs={"pk": node.id}
        )
        response = self.client.post(
            supply_chain_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_product(self):
        """Test to list and create Products based on a supplychain."""
        product_url = reverse("admin-supply-chain")
        with open(self.file_path, "rb") as fp:
            data = {
                "name": "Apple orange",
                "supply_chain": "J0Bxp",
                "description": "Apple",
                "file": fp,
            }

            response = self.client.post(product_url, data, **self.headers)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            response = self.client.get(
                product_url, format="json", **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_product_update(self):
        """Test to retrieve supply chain details."""
        product = mixer.blend(Product, supply_chain=self.supply_chain)
        admin_product_url = reverse(
            "admin-product-update", kwargs={"pk": product.id}
        )
        data = {"name": self.faker.name()}
        response = self.client.patch(
            admin_product_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_node_theme(self):
        """Test to create node theme."""
        node_theme_url = reverse(
            "admin-node-theme", kwargs={"pk": self.company.id}
        )
        data = {
            "consumer_interface_theming": "true",
            "dashboard_theming": "true",
        }
        response = self.client.post(
            node_theme_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_verifier(self):
        """Test to create node verifier."""
        admin_verifier_url = reverse(
            "admin-verifier", kwargs={"pk": self.company.id}
        )
        data = {"supply_chain": [self.supply_chain.idencode]}
        response = self.client.post(
            admin_verifier_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_verifier_destroy(self):
        """Test to destroy node verifier."""
        mixer.blend(
            Verifier, node=self.company, supply_chain=self.supply_chain
        )
        data = {"supply_chain": self.supply_chain.idencode}
        admin_verifier_url = reverse(
            "admin-verifier", kwargs={"pk": self.company.id}
        )
        response = self.client.delete(
            admin_verifier_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
