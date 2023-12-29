from django.urls import reverse
from mixer.backend.django import mixer
from rest_framework import status
from v2.reports.constants import STOCK
from v2.reports.models import Export
from v2.reports.tests.integration.base import ReportsBaseTestCase


class ReportTestCase(ReportsBaseTestCase):
    def setUp(self):
        super(ReportTestCase, self).setUp()
        mixer.blend(Export, node=self.company, export_type=STOCK)

    def test_generate_sheet(self):
        url = reverse("exports-list")
        data = {
            "export_type": STOCK,
            "filters": '{"search":"a"}',
            "file_type": 1,
        }
        response = self.client.post(
            url, data=data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_generate_sheet(self):
        url = reverse("exports-list")
        response = self.client.get(url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_generate_sheet(self):
        export = Export.objects.last()
        url = reverse("exports-detail", kwargs={"pk": export.idencode})
        response = self.client.get(url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
