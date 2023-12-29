# """Tests of the app bulk templates."""
# import unittest
#
# from common import library as common_lib
# from django.conf import settings
# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APIClient
# from v2.accounts.models import AccessToken
# from v2.accounts.models import FairfoodUser
# from v2.bulk_templates import constants as temp_const
# from v2.bulk_templates.models import Template
# from v2.bulk_templates.models import TemplateTypeField
# from v2.supply_chains.models import NodeSupplyChain
#
#
# # Create your tests here.
# PA = "/v2/bulk_templates/tests/Bulk_upload_template_10-05-2022_123441.xlsx"
#
#
# class TemplateTestCase(unittest.TestCase):
#     def setUp(self):
#         self.client = APIClient()
#         # self.user = FairfoodUser.objects.get(
#         #     email_verified=True, email='gopika+601@cied.in')
#         self.user = FairfoodUser.objects.filter(
#             email_verified=True,
#             auth_token__key__isnull=False,
#             default_node__isnull=False,
#         ).last()
#         token = AccessToken.objects.filter(user__id=self.user.id).first()
#         self.node = self.user.default_node.idencode
#         self.header = {
#             "HTTP_BEARER": token.key,
#             "HTTP_USER_ID": self.user.idencode,
#             "HTTP_NODE_ID": self.node,
#         }
#         self.template_path = (
#             settings.BASE_DIR + "/v2/bulk_templates/tests/"
#             "Bulk_upload_template_10-05-2022_123441.xlsx"
#         )
#         nsc = NodeSupplyChain.objects.filter(
#             node_id=common_lib._decode(self.node)
#         ).first()
#         self.sc = nsc.supply_chain.idencode
#         self.product = nsc.supply_chain.products.first().idencode
#
#     def test_template(self):
#         """Test for create template."""
#         template_url = reverse(
#             "<class 'v2.bulk_templates.models.Template'>-list"
#         )
#         with open(self.template_path, "rb") as fp:
#             data = {"file": fp}
#             response = self.client.post(template_url, data, **self.header)
#             self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         Template.objects.get(
#             id=common_lib._decode(response.data["id"])
#         ).delete()
#
#     def test_list_template(self):
#         """Test for list templates."""
#         temp_url = reverse(
#         "<class 'v2.bulk_templates.models.Template'>-list")
#         response = self.client.get(temp_url, format="json", **self.header)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_template_preview(self):
#         """Test for preview templates."""
#         self.temp_id = Template.objects.last().idencode
#         temp_url = reverse(
#             "<class 'v2.bulk_templates.models.Template'>-preview",
#             kwargs={"pk": self.temp_id},
#         )
#         response = self.client.get(temp_url, format="json", **self.header)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_template_name_validate(self):
#         """Test to validate template name."""
#
#         self.validate_temp_name_url = reverse(
#             "<class 'v2.bulk_templates.models.Template'>-validate-name"
#         )
#         data = {"name": "Apple Transaction"}
#         self.header["format"] = "json"
#         response = self.client.post(
#             self.validate_temp_name_url, data, **self.header
#         )
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_link_template(self):
#         """Test for link templates."""
#         template_url = reverse(
#             "<class 'v2.bulk_templates.models.Template'>-list"
#         )
#         with open(self.template_path, "rb") as fp:
#             data = {"file": fp}
#             response = self.client.post(template_url, data, **self.header)
#         # print("@@@@@@@@@@@@@@ validate link temp create", response.content)
#         temp_id = response.data["id"]
#         temp_url = reverse(
#             "<class 'v2.bulk_templates.models.Template'>-detail",
#             kwargs={"pk": temp_id},
#         )
#         temp_type_field = TemplateTypeField.objects.filter(
#             template_type=temp_const.TEMPLATE_TYPE_TXN
#         )
#         data = {
#             "name": "popilol",
#             "is_saved": "True",
#             "title_row": 10,
#             "data_row": 20,
#             "type_fields": [
#                 {"id": temp_type_field[0].idencode, "column_pos": "b"},
#                 {"id": temp_type_field[1].idencode, "column_pos": "d"},
#                 {"id": temp_type_field[2].idencode, "column_pos": "g"},
#                 {"id": temp_type_field[3].idencode, "column_pos": "e"},
#             ],
#         }
#         response = self.client.patch(
#             temp_url, data, format="json", **self.header
#         )
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         Template.objects.get(id=common_lib._decode(temp_id)).delete()
#
#     def test_verify_template(self):
#         """Test for create bulk Products based on a supply chain."""
#         template_url = reverse(
#             "<class 'v2.bulk_templates.models.Template'>-list"
#         )
#         with open(self.template_path, "rb") as fp:
#             data = {"file": fp}
#             response = self.client.post(template_url, data, **self.header)
#         temp_id = response.data["id"]
#         template_verify_url = reverse(
#             "<class 'v2.bulk_templates.models.Template'>-verify"
#         )
#         with open(self.template_path, "rb") as fp:
#             data = {
#                 "file": fp,
#                 "product": self.product,
#                 "unit": 1,
#                 "currency": "USD",
#                 "supply_chain": self.sc,
#                 "temp_id": temp_id,
#             }
#             response = self.client.post(
#                 template_verify_url, data, **self.header
#             )
#             self.assertEqual(response.status_code, status.HTTP_200_OK)
#         Template.objects.get(id=common_lib._decode(temp_id)).delete()
#
#     def test_template_type_field_list(self):
#         """Test for list template_type_fields."""
#         temp_type = 1
#         temp_url = reverse("template-field-type", kwargs={"type": temp_type})
#         response = self.client.get(temp_url, format="json", **self.header)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_bulk_create(self):
#         """Test for bulk create templates."""
#         template_url = reverse(
#             "<class 'v2.bulk_templates.models.Template'>-list"
#         )
#         with open(self.template_path, "rb") as fp:
#             data = {"file": fp}
#             response = self.client.post(template_url, data, **self.header)
#         temp_id = response.data["id"]
#         bulk_file = response.data["bulk_file"]
#         temp_url = reverse(
#             "<class 'v2.bulk_templates.models.DynamicBulkUpload'>-detail",
#             kwargs={"pk": bulk_file},
#         )
#         data = {
#             "product": self.product,
#             "currency": "USD",
#             "unit": 1,
#             "node": self.node,
#             "row_data": [
#                 {"quantity": "20", "price": 2, "date": "2022-01-03"},
#                 {"quantity": "20", "price": 5, "date": "2022-01-03"},
#                 {"quantity": "20", "price": 8, "date": "2022-01-03"},
#             ],
#         }
#         response = self.client.patch(
#             temp_url, data, format="json", **self.header
#         )
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         Template.objects.get(id=common_lib._decode(temp_id)).delete()
#
#     def test_farmer_validate(self):
#         """Test to validate farmer."""
#         self.validate_farmer_url = reverse("validate_farmer")
#         nsc = NodeSupplyChain.objects.filter(
#             node_id=common_lib._decode(self.node)
#         ).first()
#         data = {
#             "id": "0405198400063",
#             "node": self.node,
#             "supply_chain": nsc.supply_chain.idencode,
#         }
#         response = self.client.post(
#             self.validate_farmer_url, data, **self.header
#         )
#         # print("@@@@@@@@@@@@@@ validate farmer", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_duplicate_txn_validate(self):
#         """Test to validate farmer."""
#         validate_txn_url = reverse("validate_duplicate_txn")
#         self.header["format"] = "json"
#         data = {
#             "date__date": "2022-1-3",
#             "source__id": self.node,
#             "product": self.product,
#             "result_batches__current_quantity": 20,
#             "result_batches__unit": 1,
#             "price": 8,
#             "currency": "USD",
#         }
#         response = self.client.post(validate_txn_url, data, **self.header)
#         # print("@@@@@@@@@@@@@@ duplicate farmer", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_template_delete(self):
#         """Test for delete templates."""
#         self.temp_id = Template.objects.first().idencode
#         temp_url = reverse(
#             "<class 'v2.bulk_templates.models.Template'>-detail",
#             kwargs={"pk": self.temp_id},
#         )
#         response = self.client.delete(temp_url, format="json", **self.header)
#         # print("@@@@@@@@@@@@@@ delete farmer", response.content)
#         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
