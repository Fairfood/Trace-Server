from django.conf import settings
from django.urls import reverse
from rest_framework import status
from v2.claims.constants import FIELD_TYPE_OPTION
from v2.claims.constants import FIELD_TYPE_TEXT
from v2.claims.models import CriterionField

from .base import ClaimBaseTestCase

PA = "/v2/bulk_templates/tests/Bulk_upload_template_10-05-2022_123441.xlsx"


class ClaimTestCase(ClaimBaseTestCase):
    def setUp(self):
        super().setUp()
        self.file_path = settings.BASE_DIR + PA

    def test_claim_list(self):
        """Test for list and create claims."""
        claim_list_url = reverse("claim-list")
        response = self.client.get(
            claim_list_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_claim(self):
        """Test for list and create claims."""
        claim_url = reverse("claim", kwargs={"pk": self.claim.id})
        data = {
            "name": "Living Income Premium",
            "scope": 1,
            "proportional": "true",
            "removable": "false",
            "inheritable": 1,
            "verified_by": 2,
        }
        response = self.client.patch(
            claim_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(claim_url, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_criterion(self):
        """Test for create criterion."""
        criterion_url = reverse("criterion")
        data = {
            "criteria": [
                {
                    "name": "test",
                    "description": "test",
                    "claim": self.claim.idencode,
                },
                {
                    "name": "hello",
                    "description": "hello",
                    "claim": self.claim.idencode,
                },
            ]
        }
        response = self.client.post(
            criterion_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_criterion_update(self):
        """Test for Update and delete criterion."""
        self.create_claim()
        criterion_url = reverse(
            "criterion-update", kwargs={"pk": self.criterion.id}
        )
        data = {"claim": self.claim.idencode}
        response = self.client.patch(
            criterion_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(
            criterion_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_criterion_field(self):
        """Test for Update and delete criterion."""
        criterion_field_url = reverse("criterion-field")
        self.create_criterion()
        data = {
            "criterion_field": [
                {
                    "title": "1",
                    "type": FIELD_TYPE_TEXT,
                    "options": [],
                    "criterion": self.criterion.idencode,
                },
                {
                    "title": "hello",
                    "type": FIELD_TYPE_OPTION,
                    "options": ["hi", "hello"],
                    "criterion": self.criterion.idencode,
                },
            ]
        }
        response = self.client.post(
            criterion_field_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_criterion_field_update(self):
        """Test for Update and delete criterion field."""
        # claim = Claim.objects.create(
        #     name='test', type=1, description_basic='description basic')
        # criterion = Criterion.objects.create(claim=claim).idencode
        criterion_field = CriterionField.objects.create(
            criterion_id=self.criterion.id, type=1, title=self.faker.name()
        )
        criterion_field_url = reverse(
            "criterion-field-update", kwargs={"pk": criterion_field.id}
        )
        data = {
            "title": self.faker.name(),
            "type": "1",
            "options": "",
            "criterion": self.criterion.idencode,
        }
        response = self.client.patch(
            criterion_field_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_transaction_attach(self):
        """Test for attach a claims to transactions."""
        transaction_attach_url = reverse("transaction-attach")
        self.change_to_node_user()
        self.create_transaction()
        data = {
            "transaction": self.transaction.idencode,
            "claims": [
                {
                    "claim": self.claim.idencode,
                    "verifier": self.company.idencode,
                }
            ],
        }

        response = self.client.post(
            transaction_attach_url, data, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # def test_transaction_data(self):
    #     """Test for add claim data to transactions."""
    #     transaction_data_url = reverse("transaction-data")
    #     # self.create_transaction()
    #     transaction_claim = TransactionClaim.objects.first()
    #     with open(self.file_path, "rb") as fp:
    #         data = {
    #             "transaction": transaction_claim.transaction.idencode,
    #             "field": transaction_claim.claim.criteria.all()[0]
    #                 .fields.all()[0]
    #                 .idencode,
    #             "file": fp,
    #             "response": "demo",
    #         }
    #
    #         response = self.client.post(
    #             transaction_data_url, data, **self.headers
    #         )
    #         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #
    # def test_batch_attach(self):
    #     """Test for attach a claims to batch."""
    #     batch_attach_url = reverse("batch-attach")
    #     attached_batch_claim = AttachedBatchClaim.objects.first()
    #     data = {
    #         "batch": attached_batch_claim.batch.idencode,
    #         "claims": [
    #             {
    #                 "claim": attached_batch_claim.claim.idencode,
    #                 "verifier": attached_batch_claim.verifier.idencode,
    #             }
    #         ],
    #     }
    #
    #     response = self.client.post(
    #         batch_attach_url, data, format="json", **self.header
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #
    # def test_batch_data(self):
    #     """Test for add claim data to batch."""
    #     batch_data_url = reverse("batch-data")
    #     _key_left_part = (
    #     "criterion__attached_criteria__attachedbatchcriterion")
    #     _key_right_part = "__batch_claim__batch"
    #     _key = _key_left_part + _key_right_part
    #     _e = {_key: None}
    #     field = CriterionField.objects.exclude(**_e).first()
    #     batch = field.criterion.attached_criteria.all()[
    #         0
    #     ].attachedbatchcriterion.batch_claim.batch
    #     with open(self.file_path, "rb") as fp:
    #         data = {
    #             "field": field.idencode,
    #             "batch": batch.idencode,
    #             "file": fp,
    #             "response": FIELD_TYPE_TEXT,
    #         }
    #         response = self.client.post(batch_data_url, data, **self.header)
    #         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #
    # def test_node_attach(self):
    #     """Test for attach a claims to company."""
    #     node_attach_url = reverse("node-attach")
    #     claim = Claim.objects.create(
    #         type=claim_constants.CLAIM_TYPE_COMPANY,
    #         scope=claim_constants.CLAIM_SCOPE_LOCAL,
    #     )
    #     claim.owners.add(self.node)
    #     claim.save()
    #     data = {"node": self.node.idencode, "claims": [claim.idencode]}
    #
    #     response = self.client.post(
    #         node_attach_url, data, format="json", **self.header
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #
    # def test_node_data(self):
    #     """Test for add claim data to company."""
    #     node_data_url = reverse("node-data")
    #     _kl = "criterion__attached_criteria__attachedcompanycriterion"
    #     _kr = "__company_claim__node"
    #     _k = _kl + _kr
    #     _f = {_k: None}
    #     field = CriterionField.objects.exclude(**_f).first()
    #     node = field.criterion.attached_criteria.all()[
    #         0
    #     ].attachedcompanycriterion.company_claim.node
    #     with open(self.file_path, "rb") as fp:
    #         data = {
    #             "field": field.idencode,
    #             "node": node.idencode,
    #             "file": fp,
    #             "response": FIELD_TYPE_TEXT,
    #         }
    #         response = self.client.post(node_data_url, data, **self.header)
    #         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #
    # def test_inheritable_claim(self):
    #     """Test for which claims can be inherited in a list of batches."""
    #     inheritable_url = reverse("inheritable")
    #     batch = Batch.objects.first()
    #     product = Product.objects.first()
    #     data = {
    #         "batches": [
    #             {"batch": batch.idencode, "quantity": 1},
    #             {"batch": batch.idencode, "quantity": 2},
    #         ],
    #         "output_products": [product.idencode],
    #     }
    #
    #     response = self.client.post(
    #         inheritable_url, data, format="json", **self.header
    #     )
    #     #
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #
    # def test_attached_claim(self):
    #     """Test for get details attached claim."""
    #     attached_claim = AttachedClaim.objects.first()
    #     attached_claim_url = reverse(
    #         "attached-claim", kwargs={"pk": attached_claim.id}
    #     )
    #     response = self.client.get(
    #         attached_claim_url, format="json", **self.header
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    # def test_attached_claim_retrieve(self):
    #     """Test for update attached claim details."""
    #     attached_claim = AttachedClaim.objects.filter(
    #         status=1, verifier__isnull=False
    #     ).first()
    #     attached_claim_url = reverse(
    #         "attached-claim", kwargs={"pk": attached_claim.id}
    #     )
    #     user = (
    #         NodeMember.objects.filter(node=attached_claim.verifier)
    #             .first()
    #             .user
    #     )
    #     token = AccessToken.objects.filter(
    #         user__id=user.id, key__isnull=False
    #     ).first()
    #     if not token:
    #         user.issue_access_token()
    #         token = AccessToken.objects.filter(
    #             user__id=user.id, key__isnull=False
    #         ).first()
    #     header = {
    #         "HTTP_BEARER": token.key,
    #         "HTTP_USER_ID": user.idencode,
    #         "HTTP_NODE_ID": attached_claim.verifier.idencode,
    #     }
    #     data = {"status": 2}
    #     response = self.client.patch(
    #         attached_claim_url, data, format="json", **header
    #     )
    #     # print("@@@@@@@@@@@@@@ response25555", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    # def test_only_verifier_can_attached_claim_retrieve(self):
    #     """Test only verifier can attached claim retrieve."""
    #     attached_claim = AttachedClaim.objects.first()
    #     attached_claim_url = reverse(
    #         "attached-claim", kwargs={"pk": attached_claim.id}
    #     )
    #     data = {"status": 2}
    #     response = self.client.patch(
    #         attached_claim_url, data, format="json", **self.header
    #     )
    #     # print("@@@@@@@@@@@@@@ response266666", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #
    # def test_attached_claim_remove(self):
    #     """Test for update verification."""
    #     attached_claim = AttachedClaim.objects.exclude(
    #         claim__verifiers=None
    #     ).first()
    #     claim = attached_claim.claim
    #     verifier = claim.verifiers.first()
    #     user = (
    #         NodeMember.objects.filter(node=attached_claim.verifier)
    #             .first()
    #             .user
    #     )
    #     token = AccessToken.objects.filter(user__id=user.id).first()
    #     header = {
    #         "HTTP_USER_ID": user.idencode,
    #         "HTTP_NODE_ID": attached_claim.verifier.idencode,
    #         "HTTP_BEARER": token.key,
    #     }
    #     attached_claim = AttachedCompanyClaim.objects.create(
    #         node_id=verifier.id,
    #         claim_id=claim.id,
    #         verifier_id=verifier.id,
    #         attached_by_id=self.node.id,
    #     )
    #     attached_claim_url = reverse(
    #         "attached-claim", kwargs={"pk": attached_claim.id}
    #     )
    #     data = {"status": 2}
    #     response = self.client.patch(
    #         attached_claim_url, data, format="json", **header
    #     )
    #     # print("@@@@@@@@@@@@@@ response277777", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    # def test_claim_details(self):
    #     """Test for get claim details."""
    #     claim = Claim.objects.first()
    #     claim_details_url = reverse(
    #         "admin-claim-details", kwargs={"pk": claim.id}
    #     )
    #     response = self.client.get(
    #         claim_details_url, format="json", **self.header
    #     )
    #     # print("@@@@@@@@@@@@@@ response2888888", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    # def test_verifiers(self):
    #     """Test for list verifiers."""
    #     verifier_url = reverse("verifier")
    #     response = self.client.get(
    #     verifier_url, format="json", **self.header)
    #     # print("@@@@@@@@@@@@@@ response2999999", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    # def test_claim_verifiers(self):
    #     """Test for list claim verifiers."""
    #     verifier_url = reverse("claim-verifiers")
    #     supply_chain = SupplyChain.objects.first()
    #     response = self.client.get(
    #         verifier_url,
    #         {"supply_chain": supply_chain.idencode},
    #         format="json",
    #         **self.header,
    #     )
    #     # print("@@@@@@@@@@@@@@ response300000", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    # def test_verification_sent(self):
    #     """Test for list verifications sent."""
    #     verification_sent_url = reverse("verification-sent")
    #     response = self.client.get(
    #         verification_sent_url, format="json", **self.header
    #     )
    #     # print("@@@@@@@@@@@@@@ response311111", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    # def test_verification_received(self):
    #     """Test for list Received verifications."""
    #     verification_received_url = reverse("verification-received")
    #     response = self.client.get(
    #         verification_received_url, format="json", **self.header
    #     )
    #     # print("@@@@@@@@@@@@@@ response322222", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    # def test_verification_details(self):
    #     """Test for update verification details."""
    #     attached_claim = AttachedClaim.objects.filter(status=1).first()
    #     user = (
    #         NodeMember.objects.filter(node=attached_claim.verifier)
    #             .first()
    #             .user
    #     )
    #     token = AccessToken.objects.filter(user__id=user.id).first()
    #     header = {
    #         "HTTP_USER_ID": user.idencode,
    #         "HTTP_NODE_ID": attached_claim.verifier.idencode,
    #         "HTTP_BEARER": token.key,
    #     }
    #     verification_received_url = reverse(
    #         "verification-details", kwargs={"pk": attached_claim.id}
    #     )
    #     data = {"name": "qwerty"}
    #     response = self.client.patch(
    #         verification_received_url, data, format="json", **header
    #     )
    #     # print("@@@@@@@@@@@@@@ response34444", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    # def test_comment(self):
    #     """Test for claim comment."""
    #     attached_claim = AttachedClaim.objects.first()
    #     comment_url = reverse("comment")
    #     data = {
    #         "verification": attached_claim.idencode,
    #         "message": "Please upload correct documents",
    #     }
    #     response = self.client.post(
    #         comment_url, data, format="json", **self.headers
    #     )
    #     # print("@@@@@@@@@@@@@@ response355555", response.content)
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_attached_node_claim(self):
        """Test for get attached node claims."""
        attached_node_claim_url = reverse(
            "attached-node-claim", kwargs={"pk": self.company.id}
        )
        response = self.client.get(
            attached_node_claim_url, format="json", **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
