from django.conf import settings
from django.urls import reverse
from rest_framework import status

from v2.accounts.models import TermsAndConditions
from v2.accounts.tests.integration.base import AuthBaseTestCase


class UserTestCase(AuthBaseTestCase):
    """Test cases for authentication APIs."""

    def setUp(self):
        super().setUp()
        self.totp_secret = settings.TOTP_TOKEN
        terms = [
            TermsAndConditions(
                title="Sample Terms 1",
                version="3.0", default=True),
            TermsAndConditions(
                title="Sample Terms 3",
                version="2.0", default=True),
        ]
        TermsAndConditions.objects.bulk_create(terms)

    def test_user_search(self):
        """Test to search user."""
        user_search_url = reverse("user-search")
        data = {
            "search": self.user.last_name,
        }
        user_search = self.client.get(user_search_url, data, **self.headers)
        self.assertEqual(user_search.status_code, status.HTTP_200_OK)

    def test_user_details(self):
        """Test to get user details."""
        user_details_url = reverse("user-details", kwargs={"pk": self.user.id})
        user_details = self.client.get(user_details_url, **self.headers)
        self.assertEqual(user_details.status_code, status.HTTP_200_OK)

        user_data = {"last_name": self.faker.last_name()}
        user_detail = self.client.patch(
            user_details_url, user_data, format="json", **self.headers
        )
        self.assertEqual(user_detail.status_code, status.HTTP_200_OK)

    def test_user_view(self):
        """Test to get user view."""

        user_url = reverse("user-view")
        company_url = reverse("company")
        data = {
            "primary_operation": self.operation.idencode,
            "name": self.faker.name(),
        }
        response = self.client.post(
            company_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        node = response.data["id"]

        user_data = {
            "last_name": self.faker.last_name(),
            "email": self.faker.email(),
            "default_node": node,
        }
        user_views = self.client.patch(
            user_url, user_data, format="json", **self.headers
        )
        self.assertEqual(user_views.status_code, status.HTTP_200_OK)

    def test_get_latest_terms_and_conditions(self):
        terms_url = reverse("terms")
        response = self.client.get(terms_url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_make_default(self):
        term = TermsAndConditions.objects.last()
        term.make_default()

    def test_admin_user_create(self):
        self.change_to_admin_user()
        user_url = reverse("admin-users-list")
        valid_user_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "securepassword",
        }
        response = self.client.post(user_url, data=valid_user_data,
                                    **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_user_list(self):
        self.change_to_admin_user()
        user_url = reverse("admin-users-list")
        response = self.client.get(user_url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)



