from django.conf import settings
from sentry_sdk import capture_message


class ReqList:
    """For representation only."""

    requests: list = []

    def add(self, item):
        """To perform function add."""
        self.requests.append(item)


class TreasuryWallet:
    """Class to handle TreasuryWallet and functions."""

    account_id = settings.TREASURY_ACCOUNT_ID
    public = ""
    private = settings.TREASURY_ENCRYPED_PRIVATE

    deferred_requests = ReqList()

    def topup_hbar(self):
        """To perform function topup_hbar."""
        capture_message("Balance low in treasury account")
