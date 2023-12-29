from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from v2.accounts.tests.integration.base import AuthBaseTestCase


class LoginTestCase(AuthBaseTestCase):
    """Login base test case."""

    def setUp(self):
        """Setting up test cases."""
        super().setUp()
        self.device_id = self.faker.ean13()

    def test_verify_email(self):
        verify_email_url = reverse("validator")
        self.user.verify_email()
        v_token = self.user.validation_tokens.last()
        email_data = {
            "token": v_token.key,
            "salt": v_token.idencode,
            "email": self.user.email,
        }
        response = self.client.post(
            verify_email_url, email_data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reset_password(self):
        verify_email_url = reverse("validator")
        self.user.reset_password()
        v_token = self.user.validation_tokens.last()
        email_data = {
            "token": v_token.key,
            "salt": v_token.idencode,
            "email": self.user.email,
        }
        response = self.client.post(
            verify_email_url, email_data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_email_with_invalid_token(self):
        verify_email_url = reverse("validator")
        self.user.verify_email()
        v_token = self.user.validation_tokens.last()
        v_token.expiry = timezone.now() - timedelta(days=1)
        v_token.save()

        email_data = {
            "token": v_token.key,
            "salt": v_token.idencode,
            "email": self.user.email,
        }
        response = self.client.post(
            verify_email_url, email_data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_email_update(self):
        verify_email_url = reverse("validator")
        self.user.request_email_update(self.faker.email())
        v_token = self.user.validation_tokens.last()
        email_data = {
            "token": v_token.key,
            "salt": v_token.idencode,
            "email": self.user.email,
        }
        response = self.client.post(
            verify_email_url, email_data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_verify_email(self):
        verify_email_url = reverse("validator")
        self.user.verify_email()
        email_data = {
            "token": self.faker.sha1(),
            "salt": "invalid",
            "email": self.user.email,
        }
        response = self.client.post(
            verify_email_url, email_data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_verify_email_token(self):
        verify_email_url = reverse("validator")
        self.user.verify_email()
        email_data = {
            "email": self.user.email,
        }
        response = self.client.get(
            verify_email_url, email_data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_login_with_unverified_email(self):
        login_url = reverse("login")
        login_data = {
            "username": self.faker.email(),
            "password": self.faker.password(),
            "device_id": self.device_id,
        }
        response = self.client.post(login_url, login_data, format="json",
                                    **self.headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authentication_without_password(self):
        login_url = reverse("login")
        response = self.client.post(login_url, {"username": self.email})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authentication_with_wrong_password(self):
        login_url = reverse("login")
        login_data = {
            "username": self.email,
            "password": self.faker.password(),
        }
        response = self.client.post(login_url, login_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
