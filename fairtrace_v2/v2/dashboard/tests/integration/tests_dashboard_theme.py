"""Tests of dashboard Theme."""
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from v2.dashboard.tests.integration.base import DashBaseTestCase

# Create your tests here.


class DashboardThemeTestCase(DashBaseTestCase):
    def setUp(self):
        super(DashboardThemeTestCase, self).setUp()
        self.totp_secret = settings.CI_TOTP_SECRET
        self.change_to_admin_user()

    def test_theme(self):
        """Test to get theme."""
        theme_url = reverse("theme")

        data = {
            "colour_primary_alpha": "#007A53",
            "colour_primary_beta": "#7FBCA9",
            "colour_primary_gamma": "#7FBCA9",
            "colour_primary_delta": "#CBE4DC",
            "colour_secondary": "#CD0B35",
            "colour_font_alpha": "#535353",
            "colour_font_beta": "#536B63",
            "colour_border_alpha": "#E8E8E8",
            "colour_border_beta": "#F3F3F3",
            "colour_background": "#FFFFFF",
            "colour_map_background": "#B5D9CD",
            "colour_map_clustor": "#536B63",
            "colour_map_marker": "#535353",
            "colour_map_selected": "#CD0B35",
            "colour_map_marker_text": "#FFFFFF",
        }
        response = self.client.patch(
            theme_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_theme(self):
        """Test to get theme."""
        theme_url = reverse("admin-theme")
        data = {
            "colour_primary_alpha": "#007A53",
            "colour_primary_beta": "#7FBCA9",
            "colour_primary_gamma": "#7FBCA9",
            "colour_primary_delta": "#CBE4DC",
            "colour_secondary": "#CD0B35",
            "colour_font_alpha": "#535353",
            "colour_font_beta": "#536B63",
            "colour_border_alpha": "#E8E8E8",
            "colour_border_beta": "#F3F3F3",
            "colour_background": "#FFFFFF",
            "colour_map_background": "#B5D9CD",
            "colour_map_clustor": "#536B63",
            "colour_map_marker": "#535353",
            "colour_map_selected": "#CD0B35",
            "colour_map_marker_text": "#FFFFFF",
        }
        response = self.client.post(
            theme_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_theme_retrieve(self):
        """Test to get theme."""
        theme_url = reverse(
            "admin-theme-retrieve", kwargs={"pk": self.d_theme.id}
        )
        data = {
            "colour_primary_alpha": "#007A53",
            "colour_primary_beta": "#7FBCA9",
            "colour_primary_gamma": "#7FBCA9",
            "colour_primary_delta": "#CBE4DC",
            "colour_secondary": "#CD0B35",
        }
        response = self.client.patch(
            theme_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_statistics(self):
        """Test to get statistics of a node to be displayed in the
        dashboard."""
        statistics_url = reverse("stats")
        response = self.client.get(
            statistics_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_configuration(self):
        """Test for related project configurations."""
        configuration_url = reverse("stats")
        response = self.client.get(
            configuration_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_theme(self):
        """Test for related project configurations."""
        public_theme_url = reverse(
            "public-theme", kwargs={"name": self.theme.name}
        )
        response = self.client.get(
            public_theme_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
