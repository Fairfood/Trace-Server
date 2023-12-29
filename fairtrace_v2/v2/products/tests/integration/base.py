from mixer.backend.django import mixer
from v2.accounts.tests.integration.base import AuthBaseTestCase
from v2.dashboard.models import CITheme
from v2.products.models import Batch
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Connection
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Invitation
from v2.supply_chains.models import NodeSupplyChain
from v2.transactions.models import ExternalTransaction
from v2.transactions.models import SourceBatch


class ProductsBaseTestCase(AuthBaseTestCase):
    def setUp(self):
        super(ProductsBaseTestCase, self).setUp()
        mixer.blend(CITheme, node=self.company, public=True)

    def create_external_transaction(self):
        farmer = mixer.blend(Farmer, type=NODE_TYPE_FARM,
                             creator=self.user, updater=self.user)
        mixer.blend(
            NodeSupplyChain,
            node=farmer,
            supply_chain=self.supply_chain,
            primary_operation=self.operation,
        )
        batch = mixer.blend(
            Batch, node=farmer, product=self.product, current_quantity=500
        )
        connection = mixer.blend(
            Connection,
            buyer=self.company,
            supplier=farmer,
            supply_chain=self.supply_chain,
        )
        mixer.blend(
            Invitation,
            inviter=self.company,
            connection=connection,
            type=1,
            invitee=farmer,
            relation=1,
        )
        connection.get_or_create_graph()
        self.transaction = mixer.blend(
            ExternalTransaction, source=farmer, destination=self.company
        )
        mixer.blend(SourceBatch, transaction=self.transaction, batch=batch)
        mixer.blend(
            Batch,
            node=self.company,
            source_transaction=self.transaction,
            product=self.product,
            current_quantity=200,
            initial_quantity=200,
        )
