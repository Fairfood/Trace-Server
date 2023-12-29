from mixer.backend.django import mixer
from v2.accounts.tests.integration.base import AuthBaseTestCase
from v2.claims.constants import CLAIM_TYPE_PRODUCT
from v2.claims.models import Claim
from v2.claims.models import Criterion
from v2.products.models import Batch
from v2.products.models import Product
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Connection
from v2.supply_chains.models import Farmer
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import SourceBatch


class ClaimBaseTestCase(AuthBaseTestCase):
    def setUp(self):
        super().setUp()
        self.change_to_admin_user()
        self.create_claim()
        self.create_criterion()
        self.create_product()
        # self.create_transaction()

    def create_claim(self):
        self.claim = Claim.objects.create(
            name=self.faker.name(),
            type=CLAIM_TYPE_PRODUCT,
            description_basic=self.faker.text(),
        )

    def create_criterion(self):
        self.criterion = Criterion.objects.create(claim=self.claim)

    def create_product(self):
        self.product = Product.objects.create(
            name=self.faker.name(), supply_chain=self.supply_chain
        )

    # def create_farmer_connection(self):
    #     """Test for farmer registration."""
    #     self.create_operation(is_farmer=True)
    #     farmer_url = reverse("farmer")
    #     data = {
    #         "first_name": self.faker.first_name(),
    #         "last_name": self.faker.last_name(),
    #         "family_members": self.faker.random_digit(),
    #         "farm_area": self.faker.street_name(),
    #         "primary_operation": self.operation.idencode,
    #         "managers": self.company.idencode,
    #     }
    #
    #     response = self.client.post(
    #         farmer_url, data, format="json", **self.headers
    #     )
    #     if response.status_code != status.HTTP_201_CREATED:
    #         raise Exception('Farmer not created.')
    #
    # def create_farmer_transaction(self):
    #     self.create_farmer_connection()
    #     farmer = Farmer.objects.last()
    #
    #     external_url = reverse("external")
    #     data = {
    #         "date": timezone.now(),
    #         "node": farmer.idencode,
    #         "type": EXTERNAL_TRANS_TYPE_INCOMING,
    #         "product": self.product.idencode,
    #         "quantity": self.faker.random_number(),
    #         "unit": 1,
    #         "comment": "New external transaction",
    #     }
    #     response = self.client.post(
    #         external_url, data, format="json", **self.headers
    #     )
    #     if response.status_code != status.HTTP_201_CREATED:
    #         raise Exception(f'Transaction not created.{response.data}')
    #     self.transaction = Transaction.objects.last()
    def create_transaction(self):
        farmer = mixer.blend(Farmer, type=NODE_TYPE_FARM, creator=self.user)
        batch = mixer.blend(Batch, node=farmer)
        mixer.blend(Connection, buyer=self.company, supplier=farmer)
        self.transaction = mixer.blend(
            ExternalTransaction, source=farmer, destination=self.company
        ).transaction_ptr
        mixer.blend(SourceBatch, transaction=self.transaction, batch=batch)
        mixer.blend(
            Batch, node=self.company, source_transaction=self.transaction
        )
