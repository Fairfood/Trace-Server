# """Tests of the claim request."""
# import unittest
#
# from django.conf import settings
# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APIClient
# from v2.accounts.models import AccessToken
# from v2.accounts.models import FairfoodUser
# from v2.claims import constants
# from v2.claims.models import Claim
# from v2.claims.models import CriterionField
# from v2.supply_chains.models import Node
# from v2.transparency_request.models import ClaimRequest
# from v2.transparency_request.models import ClaimRequestField
#
# # Create your tests here.
# PA = "/v2/bulk_templates/tests/Bulk_upload_template_10-05-2022_123441.xlsx"
#
#
# class ClaimRequestTestCase(unittest.TestCase):
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
#         self.claim = Claim.objects.create(
#             type=constants.CLAIM_TYPE_COMPANY,
#             scope=constants.CLAIM_SCOPE_LOCAL,
#         )
#         self.claim.owners.add(self.node)
#         self.claim.save()
#         self.requestee = Node.objects.first()
#         self.claim_req = ClaimRequest.objects.create(
#             claim=self.claim, requestee=self.requestee, requester=self.node
#         )
#         self.file_path = settings.BASE_DIR + PA
#
#     def test_claim_request(self):
#         """Test for get claim requests."""
#         claim_url = reverse("claim")
#         data = {
#             "node": self.node.idencode,
#             "claim": self.claim.idencode,
#             "note": "demo public claim",
#         }
#         response = self.client.post(
#             claim_url, data, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response1", response.content)
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#
#     def test_claim_request_details(self):
#         """Test for list and update claim request details."""
#         claim_req = ClaimRequest.objects.first()
#         claim_url = reverse("claim-details", kwargs={"pk": claim_req.id})
#         response = self.client.get(claim_url, format="json", **self.header)
#         # print("@@@@@@@@@@@@@@ response1", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_claim_retrieve(self):
#         """Test for list and update claim request details."""
#         claim_url = reverse(
#         "claim-details", kwargs={"pk": self.claim_req.id})
#         data = {"response": "demo response", "status": 3}
#         response = self.client.patch(
#             claim_url, data, format="json", **self.header
#         )
#         # print("@@@@@@@@@@@@@@ response 2 ", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_claim_field(self):
#         """Test to retrieve claim request field details."""
#         criterion_field = CriterionField.objects.first()
#         claim_field = ClaimRequestField.objects.create(
#             claim_request=self.claim_req, field=criterion_field
#         )
#         claim_url = reverse("claim-field", kwargs={"pk": claim_field.id})
#         with open(self.file_path, "rb") as fp:
#             data = {"response": "1", "file": fp}
#             response = self.client.patch(claim_url, data, **self.header)
#             # print("@@@@@@@@@@@@@@ response1", response.content)
#             self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_claim_attach(self):
#         """Test to attach a claim after the requestee has added the
#         files/fields."""
#         claim_url = reverse("claim-attach", kwargs={"pk": self.claim_req.id})
#         response = self.client.post(claim_url, format="json", **self.header)
#         # print("@@@@@@@@@@@@@@ response1", response.content)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_only_receiver_can_attach_claim(self):
#         """Test to attach a claim after the requestee has added the
#         files/fields."""
#         claim_request = ClaimRequest.objects.create(
#             requester=self.requestee, requestee=self.node
#         )
#         claim_url = reverse("claim-attach", kwargs={"pk": claim_request.id})
#         response = self.client.post(claim_url, format="json", **self.header)
#         # print("@@@@@@@@@@@@@@ response1", response.content)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
