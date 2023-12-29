import pyotp
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from v2.accounts.constants import VTOKEN_TYPE_MAGIC_LOGIN, VTOKEN_TYPE_OTP
from v2.accounts.models import UserDevice, ValidationToken
from v2.accounts.tests.integration.base import AuthBaseTestCase

User = get_user_model()


class AuthTestCase(AuthBaseTestCase):
    """Auth test case."""

    def setUp(self):
        """Setting up test cases."""
        super().setUp()
        self.device_id = self.faker.ean13()

    def test_password_login(self):
        """Test for password based login."""

        # verify credentials
        url = reverse("login")
        data = {
            "username": self.email,
            "password": self.password,
            "device_id": self.device_id,
        }
        response = self.client.post(url, data, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # get login token.
        url = reverse("magic-login")
        data = {
            "validation_token": response.data["token"],
            "user_id": response.data["user_id"],
            "device_id": self.device_id,
            "salt": response.data["salt"],
        }
        response = self.client.post(url, data, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue("token" in response.data)

    def test_reset_password(self):
        """Test to reset password."""
        reset_password_url = reverse("forgot-password")
        user_data = {"email": self.email}

        response = self.client.post(reset_password_url, user_data,
                                    **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_set_password(self):
        """Test to set password."""
        # generate validation_token
        self.user.reset_password()
        set_password_url = reverse("set-password")
        self.password = self.faker.password()  # new_password
        v_token = self.user.validation_tokens.last()
        user_data = {
            "token": v_token.key,
            "salt": v_token.idencode,
            "password": self.password,
        }
        response = self.client.post(set_password_url, user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_magic_link_login(self):
        """Test to generate magic link and login with magic link."""
        magic_generate_url = reverse("magic-generate")
        magic_login_url = reverse("magic-login")
        user_data = {"email": self.email}
        response = self.client.post(magic_generate_url, user_data,
                                    **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # getting token and device id from DB instead from email.
        v_token = self.user.validation_tokens.get(type=VTOKEN_TYPE_MAGIC_LOGIN)
        login_data = {
            "user_id": self.user.idencode,
            "validation_token": v_token.key,
            "device_id": self.device_id,
            "salt": v_token.idencode
        }
        response = self.client.post(magic_login_url, login_data,
                                    **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_logout(self):
        """Test to logout."""
        logout_url = reverse("logout")
        user_data = {"device_id": self.device_id}
        response = self.client.post(
            logout_url, user_data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ValidateUsernamePasswordTestCase(AuthBaseTestCase):
    def setUp(self):
        # Create a user with a valid TOTP secret
        self.user = User.objects.create_user(
            username='test@example.com',
            password='testpassword',
            email='test@example.com',
            terms_accepted=True,
            privacy_accepted=True,
            email_verified=True,
        )
        self.totp_secret = settings.LOGIN_TOTP_SECRET

    def get_http_otp(self):
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()

    def test_validate_username_available(self):
        # Ensure the view returns valid and available as True for an available
        # username
        url = reverse('validate-username')
        data = {'username': 'testfalse@example.com'}
        response = self.client.post(url, data, HTTP_OTP=self.get_http_otp(),
                                    HTTP_TIMEZONE='UTC', HTTP_LANGUAGE='en')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['valid'], True)
        self.assertEqual(response.data['data']['available'], True)

    def test_validate_username_not_available(self):
        # Ensure the view returns valid as False and available as False for an
        # unavailable username
        url = reverse('validate-username')
        data = {'username': self.user.username}
        response = self.client.post(url, data, HTTP_OTP=self.get_http_otp(),
                                    HTTP_TIMEZONE='UTC', HTTP_LANGUAGE='en')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['valid'], True)
        self.assertEqual(response.data['data']['available'], False)

    def test_validate_username_not_valid(self):
        url = reverse('validate-username')
        data = {'username': 'test_false_example'}
        response = self.client.post(url, data, HTTP_OTP=self.get_http_otp(),
                                    HTTP_TIMEZONE='UTC', HTTP_LANGUAGE='en')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['valid'], False)
        self.assertEqual(response.data['data']['available'], False)

    def test_validate_username_no_otp(self):
        # Ensure the view returns 401 Unauthorized when no OTP is provided
        url = reverse('validate-username')
        data = {'username': 'newuser'}
        response = self.client.post(url, data, HTTP_TIMEZONE='UTC',
                                    HTTP_LANGUAGE='en')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_password(self):
        url = reverse('validate-password')
        data = {'password': self.faker.password()}
        response = self.client.post(url, data, HTTP_OTP=self.get_http_otp(),
                                    HTTP_TIMEZONE='UTC', HTTP_LANGUAGE='en')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['valid'], True)

    def test_invalid_password(self):
        url = reverse('validate-password')
        data = {'password': '1234'}
        response = self.client.post(url, data, HTTP_OTP=self.get_http_otp(),
                                    HTTP_TIMEZONE='UTC', HTTP_LANGUAGE='en')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['valid'], False)


class CreateUserDeviceTestCase(AuthBaseTestCase):

    def test_create_user_device(self):
        url = reverse("user-device")
        user_device_data = {
            "device_id": "device_id_123",
        }
        response = self.client.post(url, data=user_device_data, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_device = UserDevice.objects.get(device_id="device_id_123")
        self.assertEqual(user_device.user, self.user)

    def tearDown(self):
        UserDevice.objects.all().delete()


class EmailLoginTestCase(AuthBaseTestCase):

    def test_valid_email_login(self):
        url = reverse("email-login")
        response = self.client.post(
            url, data={"email": self.user.email}, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_email_login(self):
        url = reverse("email-login")
        response = self.client.post(
            url, data={"email": "nonexistent@example.com"}, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid email.", str(response.data))

    def test_missing_email(self):
        url = reverse("email-login")
        response = self.client.post(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email is required.", str(response.data))


class EmailLoginCodeTestCase(AuthBaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("code-verify")
        self.valid_token = ValidationToken.objects.create(
            user=self.user, key="123456", type=VTOKEN_TYPE_OTP
        )

    def test_valid_email_code(self):
        response = self.client.post(
            self.url, data={"email": self.user.email, "code": "123456"},
            **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_email_code(self):
        response = self.client.post(
            self.url, data={"email": self.user.email, "code": "654321"},
            **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid code.", str(response.data))

    def test_unverified_email_code(self):
        self.user.email_verified = False
        self.user.save()
        response = self.client.post(
            self.url, data={"email": self.user.email, "code": "123456"},
            **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_missing_email_code(self):
        response = self.client.post(self.url, data={"email": self.user.email},
                                    **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email and code is required.", str(response.data))

    def test_wrong_email(self):
        response = self.client.post(
            self.url, data={"email": self.faker.email(), "code": "123456"},
            **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_code(self):
        self.valid_token.invalidate()
        response = self.client.post(
            self.url, data={"email": self.user.email, "code": "123456"},
            **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class InviteeUserViewSetTestCase(AuthBaseTestCase):
    def setUp(self):
        super().setUp()
        self.token = ValidationToken.objects.create(user=self.user,
                                                    key="123456")
        self.salt = self.token.idencode
        self.query_params = f"token={self.token.key}&salt={self.salt}"
        self.url = reverse("invitee-user-detail",
                           args=[self.user.id])  # Replace with actual URL

    def test_list_single_object(self):
        response = self.client.get(f"{self.url}?{self.query_params}",
                                   **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_update_user(self):
        data = {
            # Provide data to update the user
        }
        response = self.client.patch(f"{self.url}?{self.query_params}", data,
                                     format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Add more assertions to verify the behavior

        # Verify member activation
        self.member.refresh_from_db()
        self.assertTrue(self.member.active)

        # Verify magic link token creation
        self.assertIn("user_id", response.data)
        self.assertIn("token", response.data)
        self.assertIn("salt", response.data)
        self.assertIn("type", response.data)

    def test_missing_token_salt(self):
        response = self.client.get(self.url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("token and salt required.", str(response.data))
        # Add more assertions to verify the behavior

    # Add more test cases to cover other scenarios
