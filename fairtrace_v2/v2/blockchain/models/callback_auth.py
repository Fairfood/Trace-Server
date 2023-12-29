"""CallBackToken Model."""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from .. import constants
from .. import library


# Create your models here.


def get_expiry():
    """Calculates the expiry date of the token."""
    return timezone.now() + timedelta(**constants.TOKEN_VALIDITY)


def get_key():
    """Generated random key automatically when saving."""
    token = get_random_string(64)
    while CallBackToken.objects.filter(key=token).exists():
        token = get_random_string(64)
    return token


class CallBackToken(models.Model):
    """Model to authenticate call back requests.

    Attributes:
        key     : Authentication Key
        status  : Status of key (Used or not)
        expiry  : Expiry time of the key (2 days from time of creation).
    """

    key = models.CharField(max_length=200, default=get_key)
    status = models.IntegerField(
        default=constants.CBTOKEN_STATUS_UNUSED,
        choices=constants.CBTOKEN_STATUS_CHOICES,
    )
    expiry = models.DateTimeField(default=get_expiry)

    updated_on = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        """Str representation."""
        return f"{self.key} {self.get_status_display()} : {self.id}"

    @property
    def idencode(self):
        """To return encoded id."""
        return library.encode(self.id)

    @property
    def is_valid(self):
        """Function  which check if Validator is valid."""
        if self.expiry > timezone.now() and (
            self.status == constants.CBTOKEN_STATUS_UNUSED
        ):
            return True
        return False

    def mark_as_used(self):
        """To mark validation token as used."""
        self.status = constants.CBTOKEN_STATUS_USED
        self.save()
        return True

    def refresh(self):
        """Function  to refresh the validation token."""
        if not self.is_valid:
            self.key = get_key()
            self.status = constants.CBTOKEN_STATUS_UNUSED
        self.expiry = get_expiry()
        self.save()
        return True

    def invalidate(self):
        """To perform function invalidate."""
        if self.status == constants.CBTOKEN_STATUS_UNUSED:
            self.expiry = timezone.now()
            self.status = constants.CBTOKEN_STATUS_INVALIDATED
            self.save()
        return True
