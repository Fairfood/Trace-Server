"""URLs of the app claims."""
from django.urls import path
from v2.claims.views import claims as claims_views
from v2.claims.views import verifications as verifications_views

urlpatterns = [
    # Claim
    path("", claims_views.ClaimsView.as_view(), name="claim-list"),
    path(
        "claim/<idencode:pk>/",
        claims_views.ClaimsRetrieveDestroyView.as_view(),
        name="claim",
    ),
    path("criterion/", claims_views.CriterionList.as_view(), name="criterion"),
    path(
        "criterion/<idencode:pk>/",
        claims_views.CriteriaRetrieveDestroyView.as_view(),
        name="criterion-update",
    ),
    path(
        "criterion-field/",
        claims_views.CriterionFieldList.as_view(),
        name="criterion-field",
    ),
    path(
        "criterion-field/<idencode:pk>/",
        claims_views.CriterionFieldRetrieveDestroyView.as_view(),
        name="criterion-field-update",
    ),
    path(
        "transaction/attach/",
        claims_views.AttachTransactionClaim.as_view(),
        name="transaction-attach",
    ),
    path(
        "transaction/data/",
        claims_views.TransactionClaimData.as_view(),
        name="transaction-data",
    ),
    path(
        "batch/attach/",
        claims_views.AttachBatchClaim.as_view(),
        name="batch-attach",
    ),
    path(
        "batch/data/", claims_views.BatchClaimData.as_view(), name="batch-data"
    ),
    path(
        "node/attach/",
        claims_views.AttachCompanyClaim.as_view(),
        name="node-attach",
    ),
    path("node/data/", claims_views.NodeClaimData.as_view(), name="node-data"),
    path(
        "inheritable/",
        claims_views.GetInheritableClaims.as_view(),
        name="inheritable",
    ),
    path(
        "attached-claim/<idencode:pk>/",
        verifications_views.AttachedClaimAPI.as_view(),
        name="attached-claim",
    ),
    path(
        "admin/", claims_views.FFAdminClaimsView.as_view(), name="claim-list"
    ),
    path(
        "admin/claim/<idencode:pk>/",
        claims_views.FFAdminClaimDetails.as_view(),
        name="admin-claim-details",
    ),
    path(
        "admin/verifier/",
        claims_views.FFAdminVerifierView.as_view(),
        name="verifier",
    ),
    # Verification
    path(
        "verifier/",
        verifications_views.ListClaimVerifiers.as_view(),
        name="claim-verifiers",
    ),
    path(
        "verification/sent/",
        verifications_views.SentVerificationListView.as_view(),
        name="verification-sent",
    ),
    path(
        "verification/received/",
        verifications_views.ReceivedVerificationListView.as_view(),
        name="verification-received",
    ),
    path(
        "verification/<idencode:pk>/",
        verifications_views.VerificationDetailsAPI.as_view(),
        name="verification-details",
    ),
    path(
        "comment/", verifications_views.CommentView.as_view(), name="comment"
    ),
    # Attached Claims
    path(
        "node/<idencode:pk>/",
        claims_views.ListAttachedNodeClaims.as_view(),
        name="attached-node-claim",
    ),
]
