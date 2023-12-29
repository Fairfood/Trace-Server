from django.urls import reverse
from rest_framework import status
from v2.activity.tests.integration.base import ActivityBaseTestCase


class ActivityTestCase(ActivityBaseTestCase):
    """Test cases for activities."""

    def test_node_activity(self):
        """Test to list node activity."""
        node_activity_url = reverse("node-activity")
        response = self.client.get(
            node_activity_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_activity(self):
        """Test to list user activity."""
        user_activity_url = reverse("user-activity")
        response = self.client.get(
            user_activity_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
