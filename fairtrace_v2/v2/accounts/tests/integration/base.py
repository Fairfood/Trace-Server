import pyotp
from django.conf import settings
from django.contrib.auth import get_user_model
from faker import Faker
from mixer.backend.django import mixer
from rest_framework import test
from v2.accounts.constants import USER_TYPE_FAIRFOOD_ADMIN
from v2.accounts.constants import USER_TYPE_NODE_USER
from v2.accounts.models import Person
from v2.supply_chains.constants import NODE_MEMBER_TYPE_ADMIN
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Company
from v2.supply_chains.models import NodeMember
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.models import Operation
from v2.supply_chains.models import OperationSupplyChain
from v2.supply_chains.models import SupplyChain

User = get_user_model()


class AuthBaseTestCase(test.APITestCase):
    """Test cases for authentication APIs."""

    faker = Faker()

    def create_user(self):
        """create user."""

        self.email = self.faker.email()
        self.password = self.faker.password()
        extra_fields = {
            "terms_accepted": True,
            "privacy_accepted": True,
            "first_name": self.faker.first_name(),
            "last_name": self.faker.last_name(),
            "email_verified": True,
        }
        self.user = User.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.password,
            **extra_fields
        )

    def create_company(self):
        """create a company."""
        faker = Faker()

        fields = {
            "type": NODE_TYPE_COMPANY,
            "registration_date": faker.date(),
            "email": faker.email(),
            "is_test": True,
            "name": faker.name(),
        }
        self.company = Company.objects.create(**fields)
        incharge = mixer.blend(Person, email=self.email)
        self.company.incharge = incharge
        self.company.save()

    def create_supply_chain(self):
        """Create a supply-chain."""
        faker = Faker()

        fields = {
            "name": faker.ean13(),
        }
        self.supply_chain = SupplyChain.objects.create(**fields)

    def create_node_member(self):
        """Create a node member."""
        fields = {
            "node": self.company,
            "user": self.user,
            "type": NODE_MEMBER_TYPE_ADMIN,
        }
        NodeMember.objects.create(**fields)

    def create_node_supply_chain(self):
        """Create a node supply-chain."""
        fields = {
            "node": self.company,
            "supply_chain": self.supply_chain,
            "active": True,
            "primary_operation": self.operation,
        }
        NodeSupplyChain.objects.create(**fields)

    def create_operation(self, is_farmer=False):
        """Create a node supply-chain."""
        if is_farmer:
            _type = NODE_TYPE_FARM
        else:
            _type = NODE_TYPE_COMPANY

        fields = {
            "node_type": _type,
            "name": self.faker.name(),
        }
        self.operation = Operation.objects.create(**fields)
        # create supply-chain map
        fields = {
            "operation": self.operation,
            "supply_chain": self.supply_chain,
            "active": True,
        }
        OperationSupplyChain.objects.create(**fields)

    @property
    def headers(self):
        return {
            "HTTP_BEARER": self.token.key,
            "HTTP_USER_ID": self.user.idencode,
            "HTTP_NODE_ID": self.company.idencode,
            "HTTP_X_IMPERSONATE": (
                "true" if self.user.is_fairtrace_admin else "false"
            ),
            "HTTP_OTP": self.get_http_otp()
        }

    def setUp(self):
        """Setting up test cases."""

        self.create_user()
        self.create_company()
        self.create_supply_chain()
        self.create_node_member()
        self.create_operation()
        self.create_node_supply_chain()
        self.user.default_node = self.company
        self.user.issue_access_token()
        self.token = self.user.auth_token.last()
        self.totp_secret = settings.LOGIN_TOTP_SECRET

    def tearDown(self):
        email = self.user.anony_email
        updated_email = self.user.anony_updated_email
        device = self.user.active_mobile_device
        self.user.logout()
        self.user.app_logout()

    def change_to_admin_user(self):
        self.user.type = USER_TYPE_FAIRFOOD_ADMIN
        self.user.save()

    def change_to_node_user(self):
        self.user.type = USER_TYPE_NODE_USER
        self.user.save()

    def get_http_otp(self):
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()
