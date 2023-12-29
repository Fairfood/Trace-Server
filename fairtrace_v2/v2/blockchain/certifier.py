"""File to manage the request header signing with private key.

Each request made from the client end need to be signed with
the client private key to authenticate them.
Requirements:
    cryptography==2.9
    PyJWT==1.7.1
"""
import os.path
import random
import time
from typing import Optional

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.serialization import NoEncryption
from cryptography.hazmat.primitives.serialization import PrivateFormat


class APIAuth:
    """Class to manage the api auth header with private key."""

    AUTH_METHOD = "JWT"
    ENCODING = "utf-8"
    DEFAULT_ALGORITHM = "RS512"
    access_key_id = ""
    signed_header = None
    context: dict = {}

    def __init__(self, access_key_id, context=None):
        """Function to initialize the verifier.

        Input Params:
            access_key_id(str): The access_key_id to authenticate as on the
                remote system.
        Returns:
            APIAuth Object
        """
        self.access_key_id = access_key_id
        self.context = context or {}

    def sign_auth_header(
        self,
        key=None,
        key_file: str = "~/.ssh/id_rsa",
        key_password: Optional[bytes] = None,
    ) -> str:
        """Create an HTTP Authorization header using a private key file.

        Either a key or a key_file must be provided.
        Input Params:
            key(str): Optional. A private key as either a string or an
                instance of cryptography.hazmat.primitives.
                    asymmetric.rsa.RSAPrivateKey.
            key_file(str): Optional. Path to a file containing the user's
                private key. Defaults to ~/.ssh/id_rsa.
                Should be in PEM format.
            key_password(str): Optional. Password to decrypt key_file.
                If set, should be a bytes object.
        Returns:
            (str): Authentication header value as a string.
        """
        if not key:
            key = self._load_private_key(key_file, key_password)
        claim = self._sign(key)
        try:
            claim = claim.decode(self.ENCODING)
        except Exception:
            claim = claim

        self.signed_header = f"{self.AUTH_METHOD} {claim}"
        return self.signed_header

    def _load_private_key(self, key_file: str, key_password=None) -> str:
        """Load a private key from disk.

        Input Params:
            key(str): Optional. A private key as either a string or an
                instance of cryptography.hazmat.primitives.
                    asymmetric.rsa.RSAPrivateKey.
            key_file(str): Optional. Path to a file containing the user's
                private key. Defaults to ~/.ssh/id_rsa.
                Should be in PEM format.
            key_password(str): Optional. Password to decrypt key_file.
                If set, should be a bytes object.
        Returns:
            (str): PrivateKey<string>
        """
        key_file = os.path.expanduser(key_file)
        key_file = os.path.abspath(key_file)

        if not key_password:
            with open(key_file, "r") as key:
                return key.read()

        with open(key_file, "rb") as key:
            key_bytes = key.read()
        return self._decrypt_key(key_bytes, key_password).decode(self.ENCODING)

    @staticmethod
    def _decrypt_key(key, password):
        """Decrypt an encrypted private key.

        Input Params:
            key(bytes): Encrypted private key as a string.
            password(bytes): Key pass-phrase.
        Returns:
            (str):Decrypted private key as a string.
        """
        private = serialization.load_pem_private_key(
            key, password=password, backend=default_backend()
        )
        return private.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        )

    def _sign(
        self, private_key: str, generate_nonce=None, iat=None, algorithm=""
    ):
        """Create a signed JWT using the given access_key_id and RSA private
        key.

        Input Params:
            access_key_id(str): access_key_id (string) to authenticate as on
            the remote system.
            private_key(str): Private key to use to sign the JWT claim.
            generate_nonce(float): Optional. Callable to use to generate a new
                nonce. Defaults to random.random
                <https://docs.python.org/3/library/random.html#random.random>`_.
            iat(str): Optional. Timestamp to include in the JWT claim.
                Defaults to `time.time
                <https://docs.python.org/3/library/time.html#time.time>
            algorithm(str): Optional. Algorithm to use to sign the
                JWT claim. Default to ``RS512``.
        Returns:
            (str):JWT claim as a string.
        """
        if not algorithm:
            algorithm = self.DEFAULT_ALGORITHM
        access_key_id = self.access_key_id
        iat = iat if iat else time.time()
        if not generate_nonce:

            def generate_nonce(access_key_id, iat):
                return random.random()  # NOQA

        token_data = {
            "access_key_id": access_key_id,
            "time": iat,
            "nonce": generate_nonce(access_key_id, iat),
            "context": self.context,
        }
        token = jwt.encode(token_data, private_key, algorithm=algorithm)
        return token
