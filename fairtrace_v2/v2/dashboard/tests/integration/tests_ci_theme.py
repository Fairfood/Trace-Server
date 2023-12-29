"""Tests of Consumer Interface Theme."""
from common import library as common_lib
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from v2.dashboard.models import CITheme
from v2.dashboard.models import ConsumerInterfaceProduct
from v2.dashboard.models import ConsumerInterfaceStage
from v2.dashboard.models import MenuItem
from v2.dashboard.tests.integration.base import DashBaseTestCase
from v2.products.models import Batch

# Create your tests here.
PA = "/v2/bulk_templates/tests/Bulk_upload_template_10-05-2022_123441.xlsx"


class CIThemeTestCase(DashBaseTestCase):
    def setUp(self):
        super(CIThemeTestCase, self).setUp()
        self.file_path = settings.BASE_DIR + PA
        self.create_external_transaction()

    def test_ci_validate_name(self):
        """Test to get theme name availability."""
        ci_validate_name_url = reverse("ci-validate-name")
        data = {"name": self.faker.first_name()}
        response = self.client.post(
            ci_validate_name_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ci_validate_batch(self):
        """Test to check if a batch can be added to a theme."""
        batch = Batch.objects.first()
        if batch:
            ci_validate_batch_url = reverse("ci-validate-batch")
            data = {
                "batch": batch.number,
                "supply_chains": [batch.product.supply_chain.idencode],
            }
            response = self.client.post(
                ci_validate_batch_url, data, format="json", **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_ci_theme(self):
        """Test for consumer interface theme."""
        ci_theme_url = reverse("ci-theme")
        data = {
            "name": self.faker.name(),
            "supply_chains": [self.supply_chain.idencode],
            "base_theme": self.theme.idencode,
            "node": self.company.idencode,
        }
        response = self.client.post(
            ci_theme_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_ci_theme_list(self):
        """Test for list consumer interface theme."""
        ci_theme_url = reverse("ci-theme")
        response = self.client.get(
            ci_theme_url,
            data={"pk": self.theme.id},
            format="json",
            **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ci_theme_retrieve(self):
        """Test for update consumer interface theme."""
        batch = Batch.objects.first()
        if batch:
            ci_theme_url = reverse(
                "ci-theme-retrieve", kwargs={"pk": self.theme.idencode}
            )
            data = {
                "name": self.faker.name(),
                "batch": batch.number,
                "primary_colour_light": "#94D3D3",
                "secondary_colour": "#700F0D",
                "text_colour": "#334739",
                "action_colour": "#EF6749",
                "brand_name": self.faker.name(),
            }
            response = self.client.patch(
                ci_theme_url, data, format="json", **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ci_theme_remove(self):
        """Test for remove consumer interface theme."""
        batch = Batch.objects.first()
        if batch:
            citheme = CITheme.objects.create(
                name=self.faker.name(),
                brand_name=self.faker.name(),
                batch_id=batch.id,
                node_id=self.company.id,
            )
            ci_theme_url = reverse(
                "ci-theme-retrieve",
                kwargs={"pk": common_lib._encode(citheme.id)},
            )
            response = self.client.delete(
                ci_theme_url, format="json", **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_ci_product(self):
        """Test to add Consumer Interface Product."""
        ci_product_url = reverse("ci-product")
        with open(self.file_path, "rb") as fp:
            data = {
                "image": fp,
                "theme": self.theme.idencode,
                "product": self.product.idencode,
                "name": self.faker.name(),
                "description": self.faker.text(),
                "location": self.faker.city(),
            }
            response = self.client.post(ci_product_url, data, **self.headers)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_ci_product_retrieve(self):
        """Test for update consumer interface product."""
        ci_product = ConsumerInterfaceProduct.objects.last()
        if ci_product:
            ci_product_url = reverse(
                "ci-product-retrieve", kwargs={"pk": "174"}
            )
            with open(self.file_path, "rb") as fp:
                data = {
                    "image": fp,
                    "name": self.faker.name(),
                    "location": self.faker.city(),
                }
                response = self.client.patch(
                    ci_product_url, data, **self.headers
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ci_product_remove(self):
        """Test for remove consumer interface product."""
        ciproduct = ConsumerInterfaceProduct.objects.last()
        if ciproduct:
            ci_product_url = reverse(
                "ci-product-retrieve", kwargs={"pk": ciproduct.id}
            )
            response = self.client.delete(
                ci_product_url, format="json", **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_ci_stage(self):
        """Test to add Consumer Interface Stage."""
        ci_stage_url = reverse("ci-stage")
        with open(self.file_path, "rb") as fp:
            data = {
                "image": fp,
                "theme": self.theme.idencode,
                "operation": self.operation.idencode,
                "title": "This stage",
                "description": self.faker.text(),
                "actor_name": self.faker.name(),
                "position": 3,
                "map_zoom_level": 5,
                "map_latitude": 0.0,
                "map_longitude": 0.0,
            }
            response = self.client.post(ci_stage_url, data, **self.headers)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_ci_stage_retrieve(self):
        """Test for update consumer interface stage."""
        stage = ConsumerInterfaceStage.objects.last()
        if stage:
            ci_stage_url = reverse(
                "ci-stage-retrieve", kwargs={"pk": stage.id}
            )
            with open(self.file_path, "rb") as fp:
                data = {
                    "image": fp,
                    "title": "The stage title",
                    "actor_name": self.faker.name(),
                }
                response = self.client.patch(
                    ci_stage_url, data, **self.headers
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ci_stage_remove(self):
        """Test for remove consumer interface product."""
        cistage = ConsumerInterfaceStage.objects.last()
        if cistage:
            ci_stage_url = reverse(
                "ci-stage-retrieve", kwargs={"pk": cistage.id}
            )
            response = self.client.delete(
                ci_stage_url, format="json", **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_ci_menu_item(self):
        """Test for consumer interface menu item."""
        ci_menu_item_url = reverse("ci-menu-item")
        data = {
            "theme": self.theme.idencode,
            "title": "Website",
            "url": "https://www.google.com/",
            "target": "_blank",
            "position": 1,
        }
        response = self.client.post(
            ci_menu_item_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_ci_menu_item_retrieve(self):
        """Test for update consumer interface menu item."""
        menu = MenuItem.objects.last()
        if menu:
            ci_menu_item_url = reverse(
                "ci-menu-item-retrieve", kwargs={"pk": menu.id}
            )
            data = {
                "title": "The stage title",
            }
            response = self.client.patch(
                ci_menu_item_url, data, **self.headers
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ci_menu_item_remove(self):
        """Test for remove consumer interface menu item."""
        cistage = MenuItem.objects.create(
            title="Website",
            position=2,
            theme_id=self.theme.id,
        )
        ci_menu_item_url = reverse(
            "ci-menu-item-retrieve", kwargs={"pk": cistage.id}
        )
        response = self.client.delete(
            ci_menu_item_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
