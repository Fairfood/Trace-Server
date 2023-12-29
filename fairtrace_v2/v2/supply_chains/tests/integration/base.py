from mixer.backend.django import mixer
from v2.accounts.tests.integration.base import AuthBaseTestCase
from v2.dashboard.models import CITheme
from v2.dashboard.models import DashboardTheme


class SupplyChainBaseTestCase(AuthBaseTestCase):
    def setUp(self):
        super(SupplyChainBaseTestCase, self).setUp()
        mixer.blend(CITheme, node=self.company, public=True)
        mixer.blend(DashboardTheme, node=self.company, public=True)
