"""Tests of communications app."""
from django.urls import reverse
from mixer.backend.django import mixer
from rest_framework import status
from v2.communications.models import Notification
from v2.communications.tests.integration.base import CommunicationBaseTestCase


# Create your tests here.


class CommunicationTestCase(CommunicationBaseTestCase):
    def test_notifications(self):
        """Test to list notifications."""
        notifications_url = reverse("notifications")
        response = self.client.get(
            notifications_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_notifications(self):
        """Test to read notifications."""
        notifications_url = reverse("notifications-read")
        response = self.client.patch(
            notifications_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_notifications_details(self):
        """Test to read notifications."""
        n = mixer.blend(Notification, user=self.user)
        notifications_url = reverse(
            "notifications-details", kwargs={"pk": n.id}
        )
        response = self.client.get(
            notifications_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
