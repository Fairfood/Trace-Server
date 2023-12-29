from v2.accounts import permissions as user_permissions
from v2.products.views.trace import TraceClaimWithBatch
from v2.products.views.trace import TraceMap
from v2.products.views.trace import TraceStagesWithBatch
from v2.products.views.trace import TraceTransactionsWithBatchActor
from v2.supply_chains import permissions as sc_permissions


class TraceClaimWithBatchForReport(TraceClaimWithBatch):
    """Claim apis for transaction report."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )


class TraceMapForReport(TraceMap):
    """Map apis for transaction report."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )


class TraceStagesWithBatchForReport(TraceStagesWithBatch):
    """Stages apis for transaction report."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )


class TraceTransactionsWithBatchActorForReport(
    TraceTransactionsWithBatchActor
):
    """Transactions apis for transaction report."""

    permission_classes = (
        user_permissions.IsAuthenticatedWithVerifiedEmail,
        sc_permissions.HasNodeAccess,
    )
