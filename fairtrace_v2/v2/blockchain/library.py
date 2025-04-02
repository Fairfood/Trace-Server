import binascii
import json

import requests
from celery import shared_task
from Crypto.Cipher import AES
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.utils.safestring import mark_safe
from hashids import Hashids
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer
from sentry_sdk import capture_exception

from . import constants


def encode(value):
    """Function to  hash hid the int value.

    Input Params:
        value(int): int value
    Returns:
        hashed string.
    """
    hasher = Hashids(
        min_length=settings.HASHHID_MIN_LENGTH, salt=settings.HASHHID_SALT
    )
    try:
        value = int(value)
        return hasher.encode(value)
    except Exception:
        return None


def decode(value):
    """Function to  decode hash hid value.

    Input Params:
        value(str): str value
    Returns:
        int value.
    """
    hasher = Hashids(
        min_length=settings.HASHHID_MIN_LENGTH, salt=settings.HASHHID_SALT
    )
    try:
        return hasher.decode(value)[0]
    except Exception:
        return None


def encrypt(message, encryption_key=settings.BLOCKCHAIN_ENCRYPTION_KEY):
    """To encrypt a message."""
    iv = str.encode(encryption_key[-16:])
    key = str.encode(encryption_key[:16])
    cipher = AES.new(key, AES.MODE_CFB, iv)
    msg = cipher.encrypt(str.encode(message))
    return binascii.hexlify(msg).decode("utf-8")


def decrypt(code, encryption_key=settings.BLOCKCHAIN_ENCRYPTION_KEY):
    """To decrypt the message."""
    iv = str.encode(encryption_key[-16:])
    key = str.encode(encryption_key[:16])
    cipher = AES.new(key, AES.MODE_CFB, iv)
    code = binascii.unhexlify(code)
    message = cipher.decrypt(code)
    return message.decode("utf-8")


@shared_task(name="post_blockchain_request", queue="low")
def post_blockchain_request(request_id):
    """Function to post the request to the blockchain middleware server.

    BlockchainRequest is fetched evey time to update values because, in
    most situations, the callback might be received before this function
    is completed, some of the values might have changed after the object
    is fetched from the db at the start of the function. Updating using
    existing object reverts these values. to avoid this, the update is
    done at the database level soon after the objects are fetched
    """
    from .models.request import BlockchainRequest

    try:
        base_request = BlockchainRequest.objects.get(id=request_id)
        request = getattr(base_request, base_request.type.lower())

        request.prepare_header()
        request.prepare_body()
        response = requests.post(
            url=settings.BC_MIDDLEWARE_BASE_URL,
            data=json.dumps(request.body, cls=DjangoJSONEncoder),
            headers=request.header,
        )
        response_json = response.json()
        BlockchainRequest.objects.filter(id=request_id).update(
            response=response_json
        )
        if not response.ok:
            BlockchainRequest.objects.filter(id=request_id).update(
                status=constants.BC_REQUEST_STATUS_FAILED
            )
            base_request.callback_token.invalidate()
            response.raise_for_status()
        BlockchainRequest.objects.filter(id=request_id).update(
            receipt=response_json["data"]["receipt"],
            last_api_call=timezone.now(),
        )
    except Exception as e:
        capture_exception(e)


def format_json_readonly(data):
    """Function to display pretty version for admin read only.

    It will do the following things,
        * Convert the data to sorted, indented JSON
        * Truncate the data. Alter as needed
        * Get the Pygments formatter
        * Highlight the data
        * Get the style sheet
        * Safe the output
    """
    response = json.dumps(data, sort_keys=True, indent=2)
    response = response[:5000]
    formatter = HtmlFormatter(style="colorful")
    response = highlight(response, JsonLexer(), formatter)
    style = "<style>" + formatter.get_style_defs() + "</style><br>"
    return mark_safe(style + response)
