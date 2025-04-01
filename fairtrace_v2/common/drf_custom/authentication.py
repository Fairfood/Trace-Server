"""Module to override the default authentication."""
import os
from django.conf import settings
from rest_framework.authentication import (
    TokenAuthentication as RestTokenAuthentication, BaseAuthentication, 
    get_authorization_header
)
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from rest_framework import exceptions
from v2.accounts.models import AccessToken
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization




class TokenAuthentication(RestTokenAuthentication):
    """Class to override the auth."""

    model = AccessToken


class JWtAuthentication(BaseAuthentication):
    """
    JWT Authentication class for Django REST Framework.

    This class provides authentication using JSON Web Tokens (JWT) for Django 
    REST Framework. It verifies the JWT token provided in the request's 
    authorization header and authenticates the user based on the token.

    Attributes:
        keyword (str): The keyword used in the authorization header to specify 
            the token type.
        verification_key_file (str): The file name of the public key used for 
            token verification.
        request (HttpRequest): The current request object.

    Methods:
        authenticate(request): Authenticates the user based on the JWT token in 
            the request's authorization header.
        validate_authorization_header(auth): Validates the authorization header 
            and extracts the token.
        authenticate_credentials(key): Authenticates the user based on the 
            token.
        get_auth_user(token): Retrieves the authenticated user based on the 
            token.
        get_user_nodes(user, token): Retrieves the nodes associated with the 
            authenticated user.
        verify_token(token): Verifies the JWT token using the public key.
        load_public_key_pem(path): Loads a public key from a PEM file.

    Raises:
        AuthenticationFailed: If the authorization header is invalid or the 
            token is expired/invalid.
    """
    
    keyword = 'Bearer'
    verification_key_file = os.path.join(settings.BASE_DIR, "public-key.pem")
    request = None

    def authenticate(self, request):
        """
        Authenticates the request based on the provided authorization header.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            User: The authenticated user if the authorization header is valid, 
            None otherwise.
        """
        self.request = request
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None
        token = self.validate_authorization_header(auth)
        return self.authenticate_credentials(token)

    def validate_authorization_header(self, auth):
        """
        Validates the authorization header.

        Args:
            auth (list): The authorization header as a list of strings.

        Returns:
            str: The token extracted from the authorization header.

        Raises:
            AuthenticationFailed: If the authorization header is invalid.
        """
        if len(auth) == 1:
            msg = _('Invalid token header. '
                    'No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        
        elif len(auth) > 2:
            msg = _('Invalid token header. '
                    'Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
            return token
        except UnicodeError:
            msg = _('Invalid token header. '
                    'Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

    def authenticate_credentials(self, key):
        """
        Authenticates the user's credentials based on the provided key.

        Args:
            key (str): The authentication key.

        Returns:
            tuple: A tuple containing the authenticated user and the key.

        """
        token = self.verify_token(key)
        user = self.get_auth_user(token)
        user_nodes = self.get_user_nodes(user, token)
        self.request.session['nodes'] = user_nodes
        self.request.session['type'] = token.get('type')
        self.request.session['email_verified'] = token.get('email_verified')
        return (user, key)

    def get_auth_user(self, token):
        """
        Retrieves the authenticated user based on the provided token.

        Args:
            token (dict): The token containing user information.

        Returns:
            User: The authenticated user.

        Raises:
            AuthenticationFailed: If the user cannot be identified.
        """
        UserModel = get_user_model()
        try:
            user_id = token["sub"]
            user_email = token["email"]
            user = UserModel.objects.get(
                sso_user_id=user_id, email=user_email
            )
        except (UserModel.DoesNotExist, KeyError):
            msg = _("Unable to identify user")
            raise exceptions.AuthenticationFailed(msg)
        return user

    def get_user_nodes(self, user, token):
        """
        Retrieves the available nodes for a given user based on the provided 
        token.

        Args:
            user (User): The user for whom to retrieve the available nodes.
            token (dict): The token containing the nodes information.

        Returns:
            QuerySet: A queryset of available nodes for the user.

        """
        token_nodes = token.get('nodes', {})
        avaliable_nodes = user.usernodes.select_related('node').filter(
            node__sso_id__in=token_nodes.keys()
        )
        return [node.node.idencode for node in avaliable_nodes]

    def verify_token(self, token):
        """
        Verifies the authenticity of a token.

        Args:
            token (str): The token to be verified.

        Returns:
            dict: The decoded token if it is valid.

        Raises:
            AuthenticationFailed: If the token has expired or is invalid.
        """
        secret_key = self.load_public_key_pem(self.verification_key_file)
        audience = settings.TRACE_OAUTH2_CLIENT_ID
        
        try:
            decoded_token = jwt.decode(
                token, secret_key, 
                algorithms=["RS256"],
                audience=audience
                )
            return decoded_token
        except jwt.ExpiredSignatureError:
            msg = _("Token has expired.")
            raise exceptions.AuthenticationFailed(msg)
        except jwt.InvalidTokenError:
            msg = _("Invalid token or signature.")
            raise exceptions.AuthenticationFailed(msg)

    @staticmethod
    def load_public_key_pem(path):
        """
        Load a public key from a PEM file.

        Args:
            path (str): The path to the PEM file.

        Returns:
            str: The public key in PEM format.

        Raises:
            FileNotFoundError: If the specified file path does not exist.
            ValueError: If the specified file is not a valid PEM file.
            cryptography.exceptions.UnsupportedAlgorithm: If the key file uses 
                an unsupported algorithm.
        """
        with open(path, 'rb') as key_file:
            key = serialization.load_pem_public_key(
                key_file.read(),
                backend=default_backend()
            )
        return key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
