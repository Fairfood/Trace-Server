# """Tests of the stock request."""
# import unittest
#
# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APIClient
# from v2.accounts.models import AccessToken
# from v2.accounts.models import FairfoodUser
# from v2.products.models import Batch
# from v2.supply_chains.models import Connection
# from v2.supply_chains.models import Node
# from v2.transparency_request import constants
# from v2.transparency_request.models import StockRequest
#
#
# # Create your tests here.
#
#
# class StockRequestTestCase(unittest.TestCase):
#     fixtures = ["operation.json"]
#
#     def setUp(self):
#         self.client = APIClient()
#         self.user = FairfoodUser.objects.filter(
#             email_verified=True,
#             auth_token__key__isnull=False,
#             default_node__isnull=False,
#         ).first()
#         token = AccessToken.objects.filter(user__id=self.user.id).first()
#         self.node = self.user.default_node
#         self.header = {
#             "HTTP_BEARER": token.key,
#             "HTTP_USER_ID": self.user.idencode,
#             "HTTP_NODE_ID": self.node.idencode,
#         }
#         self.product = (
#             Batch.objects.filter(node=self.node, product__isnull=False)
#             .first()
#             .product
#         )
#         self.requestee = Node.objects.first()
#         self.conn = Connection.objects.filter(supplier=self.node).first()
#         self.stock_req = StockRequest.objects.create(
#             connection=self.conn,
#             requestee=self.node,
#             requester=self.requestee,
#             product=self.product,
#         )
#
#     # TODO: rewrite logic.
#     # def test_stock(self):
#     #     """
#     #     Test for list and create stock.
#     #     """
#     #
#     #     claim = Claim.objects.first()
#     #     stock_url = reverse("stock")
#     #     data = {
#     #         "supplier": self.requestee.idencode,
#     #         "product": self.product.idencode,
#     #         "quantity": 1,
#     #         "unit": 1,
#     #         "claims": [claim.idencode, ]
#     #     }
#     #     response = self.client.post(
#     #         stock_url, data, format='json', **self.header)
#     #     raise Exception(response.data)
#     #
#     #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#     #     response = self.client.get(
#     #         stock_url, format='json', **self.header)
#     #     # print("@@@@@@@@@@@@@@ response1", response.content)
#     #     self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_stock_verify(self):
#         """Test to verify if a list of batches can be used for a
#         transaction."""
#         batch = Batch.objects.filter(node=self.node).first()
#         stock_verify_url = reverse("stock-verify")
#         data = {
#             "transparency_request": self.stock_req.idencode,
#             "batches": [
#                 batch.idencode,
#             ],
#         }
#         response = self.client.post(
#             stock_verify_url, data, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response1", response.content)
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#
#     def test_stock_retrieve(self):
#         """Test for update transparency request."""
#         stock_retrieve_url = reverse(
#             "stock-retrieve", kwargs={"pk": self.stock_req.id}
#         )
#         data = {
#             "status": constants.TRANSPARENCY_REQUEST_STATUS_DECLINED,
#             "response": "rejected",
#         }
#         response = self.client.patch(
#             stock_retrieve_url, data, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response1", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_stock_remove(self):
#         """Test for delete transparency request."""
#         self.stock_req = StockRequest.objects.create(
#             connection=self.conn,
#             requestee=self.requestee,
#             requester=self.node,
#             product=self.product,
#         )
#         stock_retrieve_url = reverse(
#             "stock-retrieve", kwargs={"pk": self.stock_req.id}
#         )
#         data = {"status": constants.TRANSPARENCY_REQUEST_STATUS_PENDING}
#         response = self.client.delete(
#             stock_retrieve_url, data, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response2", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_only_sender_can_remove_stock(self):
#         """Test for only the sender of the Transparency request can delete
#         it."""
#         stock_retrieve_url = reverse(
#             "stock-retrieve", kwargs={"pk": self.stock_req.id}
#         )
#         data = {"status": constants.TRANSPARENCY_REQUEST_STATUS_PENDING}
#         response = self.client.delete(
#             stock_retrieve_url, data, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response2", response.content)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#
#     def test_remove_stock_only_is_modifiable(self):
#         """Test for only remove Transparency request is modifiable."""
#         stock_retrieve_url = reverse(
#             "stock-retrieve", kwargs={"pk": self.stock_req.id}
#         )
#         data = {"status": constants.TRANSPARENCY_REQUEST_STATUS_PENDING}
#         response = self.client.delete(
#             stock_retrieve_url, data, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response2", response.content)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
