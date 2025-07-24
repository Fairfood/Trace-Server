from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from common.library import decode
from common.exceptions import BadRequest
from v2.claims.constants import STATUS_APPROVED
from v2.claims.models import GuardianClaim
from v2.guardian.constants import guardian_policies
from .claim_status import check_claim_status


class CheckClaimStatusView(generics.GenericAPIView):
    """View to check the status of claim in guardian and update"""
    
    def get(self, request, *args, **kwargs):
        guardian_claim_id = request.query_params.get('guardian_claim')
        filter_value = request.query_params.get('filter_value')

        try:
            GuardianClaim.objects.get(id=decode(guardian_claim_id))
        except Exception as e:
            raise BadRequest(f"Invalid Claim: {e}", send_to_sentry=False)
        
        claim_status = check_claim_status(filter_value, guardian_claim_id)

        return Response(
            {'claim_status': claim_status}, status=status.HTTP_200_OK
        )