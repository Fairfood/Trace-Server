# """Tests of the connection request."""
# import unittest
#
# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APIClient
# from v2.accounts.models import AccessToken
# from v2.accounts.models import FairfoodUser
# from v2.supply_chains.models import Node
# from v2.supply_chains.models import NodeSupplyChain
# from v2.transparency_request.models import ConnectionRequest
#
#
# # Create your tests here.
#
#
# class ConnectionRequestTestCase(unittest.TestCase):
#     fixtures = ["operation.json"]
#
#     def setUp(self):
#         self.client = APIClient()
#         self.user = FairfoodUser.objects.filter(
#             email_verified=True,
#             auth_token__key__isnull=False,
#             default_node__isnull=False,
#         ).last()
#         token = AccessToken.objects.filter(user__id=self.user.id).first()
#         self.node = self.user.default_node
#         self.header = {
#             "HTTP_BEARER": token.key,
#             "HTTP_USER_ID": self.user.idencode,
#             "HTTP_NODE_ID": self.node.idencode,
#         }
#         sc = (
#             NodeSupplyChain.objects.filter(node=self.node).first().supply_chain
#         )
#         # print("self.claim@@@@@@@@@@@@@@@@@", self.claim)
#         self.requestee = Node.objects.first()
#         self.conn_req = ConnectionRequest.objects.create(
#             supply_chain=sc, requestee=self.requestee, requester=self.node
#         )
#
#     # TODO: rewrite the logic.
#     # def test_connection(self):
#     #     """
#     #     Test to create connection requests.
#     #     """
#     #     sc = NodeSupplyChain.objects.filter(
#     #     node=self.node).first().supply_chain
#     #     node = self.node.get_buyers(supply_chain=sc).first()
#     #     connection_url = reverse("connection")
#     #     data = {
#     #             "node": node.idencode,
#     #             "supply_chain": sc.idencode,
#     #             "note": "Hello there"
#     #         }
#     #     response = self.client.post(
#     #         connection_url, data, format='json', **self.header)
#     #     # print("@@@@@@@@@@@@@@ response1", response.content)
#     #     self.assertEqual(response.status_code,
#     #                      status.HTTP_201_CREATED)
#
#     def test_connection_details(self):
#         """Test to list connection requests."""
#         connection_url = reverse(
#             "connection-details", kwargs={"pk": self.conn_req.id}
#         )
#         response = self.client.get(
#             connection_url, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response1", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_connection_retrieve(self):
#         """Test to retrieve connection requests details."""
#         connection_url = reverse(
#             "connection-details", kwargs={"pk": self.conn_req.id}
#         )
#         # ConnectionRequest.objects.filter(id=985).update(status=1)
#         data = {"response": "sample response note", "status": 4}
#         response = self.client.patch(
#             connection_url, data, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response2", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_transparency_request(self):
#         """Test to list transparency requests."""
#         transparency_request_url = reverse("transparency-request")
#         response = self.client.get(
#             transparency_request_url, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response1", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
