"""Views for blockchain."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import ValidCallBackToken


class UpdateBlockchainHashAPI(APIView):
    """Class to handle UpdateBlockchainHashAPI and functions."""

    permission_classes = (ValidCallBackToken,)

    @staticmethod
    def post(request, token, *args, **kwargs):
        """To perform function post."""
        token.request.manage_callback(request.data)
        response = {
            "success": True,
            "detail": "Success.",
            "code": status.HTTP_200_OK,
        }
        return Response(response, status=status.HTTP_200_OK)
