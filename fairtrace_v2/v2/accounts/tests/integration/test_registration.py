from django.conf import settings
from django.urls import reverse
from rest_framework import status
from v2.accounts.tests.integration.base import AuthBaseTestCase


class RegistrationTestCase(AuthBaseTestCase):
    """Registration test case."""
    def setUp(self):
        """Setting up test cases."""
        super().setUp()
        self.totp_secret = settings.LOGIN_TOTP_SECRET

    def test_registration(self):
        """Test for user registration."""
        signup_url = reverse("signup")
        user_data = {
            "first_name": self.faker.first_name(),
            "last_name": self.faker.last_name(),
            "email": self.faker.email(),
            "phone": self.faker.phone_number(),
            "address": self.faker.address(),
            "terms_accepted": "True",
            "privacy_accepted": "True",
            "password": self.faker.password(),
        }
        self.response = self.client.post(signup_url, user_data,
                                         format="json", **self.headers)
        self.assertEqual(self.response.status_code, status.HTTP_201_CREATED)

    def test_operation(self):
        """Test for get operation details."""
        operation_url = reverse("operations")
        response = self.client.get(
            operation_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_countries(self):
        """Test for get country details."""
        country_url = reverse("countries")

        response = self.client.get(country_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_valid_company_name(self):
        """Test to verify that a post call with valid company name."""
        self.validate_company_url = reverse("validate_company_name")
        user_data = {"name": self.faker.name()}
        response = self.client.post(
            self.validate_company_url, user_data, **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_company(self):
        """Test for company registration."""
        company_url = reverse("company")
        data = {
            "name": self.faker.name(),
            "type": 3,
            "primary_operation": self.operation.idencode,
        }
        response = self.client.post(
            company_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
