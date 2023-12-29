"""This file is to convert id."""
from common.library import _decode
from common.library import _encode
from django.conf import settings


class IDConverter:
    """Converter to convert encoded id in url to integer id."""

    regex = "[0-9a-zA-Z]{%d,}" % settings.HASHHID_MIN_LENGTH

    def to_python(self, value):
        """To perform function to_python."""
        return _decode(value)

    def to_url(self, value):
        """To perform function to_url."""
        return _encode(value)
