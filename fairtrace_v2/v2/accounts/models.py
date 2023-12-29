"""Models of the app Accounts."""
from __future__ import unicode_literals

from datetime import timedelta

from common import vendors
from common.library import _anonymise_email
from common.library import _date_time_desc
from common.library import _encode
from common.library import _get_file_path
from common.models import AbstractBaseModel
from django.conf import settings
from django.contrib.auth.models import AbstractUser as DjangoAbstractUser
from django.contrib.postgres import fields
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from fcm_django.models import AbstractFCMDevice
from v2.communications import constants as comm_const
from v2.communications.models import Notification
from v2.transactions import constants as trans_constants

from .constants import DEVICE_TYPE_ANDROID
from .constants import DEVICE_TYPE_CHOICESS
from .constants import LANGUAGE_CHOICES
from .constants import LANGUAGE_ENG
from .constants import MESSAGE_USER_OTP
from .constants import MOBILE_DEVICE_TYPES
from .constants import TOKEN_VALIDITY
from .constants import USER_STATUS_CHOICES
from .constants import USER_STATUS_COMPANY_ADDED
from .constants import USER_STATUS_CREATED
from .constants import USER_TYPE_CHOICES
from .constants import USER_TYPE_FAIRFOOD_ADMIN
from .constants import USER_TYPE_FAIRFOOD_MANAGER
from .constants import USER_TYPE_NODE_USER
from .constants import VTOKEN_STATUS_CHOICES
from .constants import VTOKEN_STATUS_UNUSED
from .constants import VTOKEN_STATUS_USED
from .constants import VTOKEN_TYPE_CHANGE_EMAIL
from .constants import VTOKEN_TYPE_CHOICES
from .constants import VTOKEN_TYPE_MAGIC_LOGIN
from .constants import VTOKEN_TYPE_OTP
from .constants import VTOKEN_TYPE_RESET_PASS
from .constants import VTOKEN_TYPE_VERIFY_EMAIL
from .managers import UserClientVersionQuerySet


class AbstractPerson(models.Model):
    """Abstract Model to store common details of a person."""

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(
        max_length=100, default="", blank=True, null=True
    )
    id_no = models.CharField(max_length=100, default="", blank=True, null=True)
    gender = models.CharField(max_length=50, default="", blank=True, null=True)
    dob = models.DateField(null=True, blank=True)
    birth_city = models.CharField(
        max_length=500, default="", blank=True, null=True
    )
    marital_status = models.CharField(
        max_length=50, default="", blank=True, null=True
    )
    email = models.EmailField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=50, default="", blank=True, null=True)

    def get_or_create_user(self):
        """Fairfood user for the corresponding person object."""
        try:
            user = FairfoodUser.objects.get(email=self.email)
            created = False
        except Exception:
            user = FairfoodUser.objects.create(
                email=self.email, username=self.email
            )
            created = True
        if created:
            user.first_name = self.first_name.title()
            user.last_name = self.last_name.title()
            user.dob = self.dob
            user.phone = self.phone
            user.status = USER_STATUS_COMPANY_ADDED
            user.save()
        return user

    class Meta:
        """Meta class for the above model."""

        abstract = True


class Person(AbstractPerson):
    """Non Abstract model for Person."""

    def __str__(self):
        """To perform function __str__."""
        return "%s %s - %d" % (self.first_name, self.last_name, self.id)


class FairfoodUser(DjangoAbstractUser):
    """User model.

    Attribs:
        external_id(str): external id of the user.
        user (obj): Django user model.
        blocked(bool): field which shows the active status of user.
        terms_accepted(bool): boolean value indicating whether the
            terms are accepted by the user.
        address(str): address of the user.
        phone (str): phone number of the user
        type (int): field define the type of the user like
            admin or Normal user etc.
        language(int): Language preference.
        image (img): user image.
        dob(datetime): date of birth of user.
    """
    external_id = models.CharField(max_length=100, default=None, blank=True, 
                                   null=True)
    dob = models.DateField(null=True, blank=True)
    phone = models.CharField(default="", max_length=200, blank=True)
    address = models.CharField(default="", max_length=2000, blank=True)
    language = models.IntegerField(
        default=LANGUAGE_ENG, choices=LANGUAGE_CHOICES
    )
    image = models.ImageField(
        upload_to=_get_file_path, null=True, default=None, blank=True
    )
    type = models.IntegerField(
        default=USER_TYPE_NODE_USER, choices=USER_TYPE_CHOICES
    )
    status = models.IntegerField(
        default=USER_STATUS_CREATED, choices=USER_STATUS_CHOICES
    )

    terms_accepted = models.BooleanField(default=False)
    privacy_accepted = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    blocked = models.BooleanField(default=False)
    updated_email = models.EmailField(null=True, blank=True, default="")

    default_node = models.ForeignKey(
        "supply_chains.Node", null=True, on_delete=models.SET_NULL, blank=True
    )

    class Meta:
        """Meta class for the above model."""

        verbose_name = "Fairfood User"

    def __str__(self):
        """Object name in django admin."""
        return "%s : %s" % (self.name, self.id)

    def save(self, *args, **kwargs):
        """To perform function save."""
        if "email" in kwargs:
            kwargs["username"] = kwargs["email"]
        super(FairfoodUser, self).save(*args, **kwargs)

    @property
    def image_url(self):
        """Get file url ."""
        try:
            return self.image.url
        except Exception:
            return None

    @property
    def name(self):
        """Get user full name."""
        return "%s" % (self.get_full_name())

    @property
    def idencode(self):
        """To return encoded id."""
        return _encode(self.id)

    @property
    def anony_email(self):
        """Property to get anonymous email."""
        return _anonymise_email(self.email)

    @property
    def anony_updated_email(self):
        """Property to get anonymous email."""
        return _anonymise_email(self.updated_email)
    
    @property
    def is_admin(self):
        """Check if user is an admin user."""
        return self.type in [
            USER_TYPE_FAIRFOOD_ADMIN,
            USER_TYPE_FAIRFOOD_MANAGER,
        ]

    def devices(self):
        """To get user devices."""
        return UserDevice.objects.filter(user=self, active=True)

    def active_mobile_device(self):
        """To get active mobile device of the user."""
        device = UserDevice.objects.filter(
            user=self, type__in=MOBILE_DEVICE_TYPES, active=True
        ).first()
        return device

    def issue_access_token(self, device=None):
        """To get or create user access token."""
        old_tokens = AccessToken.objects.filter(device=device, user=self)
        if old_tokens.count() > 1:
            old_tokens.exclude(id=old_tokens.first().id).delete()
        token, created = AccessToken.objects.get_or_create(
            device=device, user=self
        )
        if device:
            device.activate()
        self.last_login = timezone.now()
        self.save()
        # if not created:
        #     token.refresh()
        return token.key

    def get_or_create_device(self, data):
        """Function for get or create user device."""
        device, created = UserDevice.objects.get_or_create(
            device_id=data["device_id"], user=self, type=data["device_type"]
        )
        device.name = data["name"]
        device.updater = self
        device.registration_id = data.get("registration_id", "")
        device.save()
        return device

    def logout(self, device_id=None):
        """Function for user to logout."""
        try:
            token = AccessToken.objects.get(user=self)
            token.refresh()
        except Exception:
            pass
        if device_id:
            devices = UserDevice.objects.filter(user=self, device_id=device_id)
            for device in devices:
                device.active = False
                device.updater = self
                device.save()
        return True

    def app_logout(self, device_id=None):
        """Function for user to app logout."""
        try:
            token = AccessToken.objects.get(
                user=self, device__device_id=device_id
            )
            token.refresh()
        except Exception:
            pass
        return True

    def reset_password(self):
        """To set password."""
        token = ValidationToken.initialize(self, VTOKEN_TYPE_RESET_PASS)
        Notification.notify(
            token=token,
            event=token,
            user=self,
            notif_type=comm_const.NOTIF_TYPE_RESET_PASSWORD,
            sender=self,
        )
        return True

    def verify_email(self):
        """To send email verification."""
        token = ValidationToken.initialize(self, VTOKEN_TYPE_VERIFY_EMAIL)
        Notification.notify(
            token=token,
            event=token,
            user=self,
            notif_type=comm_const.NOTIF_TYPE_VERIFY_EMAIL,
            sender=self,
        )
        return True

    def sent_otp(self):
        """Function to send otp to login."""

        # get active token
        token = ValidationToken.objects.filter(
            user=self,
            type=VTOKEN_TYPE_OTP,
            status=VTOKEN_STATUS_UNUSED,
            expiry__gt=timezone.now(),
        ).last()

        if not token:
            # initiate new.
            token = ValidationToken.initialize(self, VTOKEN_TYPE_OTP)

        Notification.notify(
            token=token,
            event=token,
            user=self,
            notif_type=comm_const.NOTIF_TYPE_EMAIL_LOGIN,
            sender=self,
        )
        return True

    def generate_magic_link(self, sent_notification=True):
        """Function to send email verification."""
        token = ValidationToken.initialize(self, VTOKEN_TYPE_MAGIC_LOGIN)

        _type = (
            comm_const.NOTIF_TYPE_MAGIC_LOGIN_ADMIN
            if self.is_fairtrace_admin
            else comm_const.NOTIF_TYPE_MAGIC_LOGIN
        )

        # Only sent notification if required.
        if sent_notification:
            Notification.notify(
                token=token,
                event=token,
                user=self,
                notif_type=_type,
                sender=self,
            )
        return token

    def update_email(self, email):
        """To perform function update_email."""
        self.email = email
        self.username = email
        self.save()
        for token in self.validation_tokens.all():
            token.invalidate()
        return True

    def request_email_update(self, email):
        """To perform function request_email_update."""
        from v2.accounts.validator import validate_username

        validator = validate_username(email)
        if not validator["valid"]:
            raise ValueError("Invalid email")
        if not validator["available"]:
            raise ValueError("Email already taken")
        self.updated_email = email
        self.save()
        token = ValidationToken.initialize(self, VTOKEN_TYPE_CHANGE_EMAIL)
        Notification.notify(
            token=token,
            event=token,
            user=self,
            notif_type=comm_const.NOTIF_TYPE_CHANGE_EMAIL,
            sender=self,
            send_to=email,
        )
        return True

    def confirm_updated_email(self):
        """Function to update the email of the user.

        Updates email and username to updated_email and sets updated
        email as blank
        """
        if self.updated_email:
            self.email = self.updated_email
            self.username = self.updated_email
            self.updated_email = ""
            self.save()
            return True
        return False

    @property
    def is_fairtrace_admin(self):
        """Check if user is an admin user."""
        return self.type in [
            USER_TYPE_FAIRFOOD_ADMIN,
            USER_TYPE_FAIRFOOD_MANAGER,
        ]


class ValidationToken(AbstractBaseModel):
    """Class to store the validation token data.

    This is a generic model to store and validate all
    sort of tokens including password setters, one time
    passwords and email validations
    Attribs:
        user(obj): user object
        req_browser(str): browser of the user requested.
        req_location(str): location of the request created.
        set_browser(str): browser of the user updated.
        set_location(str): location of the request updated.
        key (str): token.
        status(int): status of the validation token
        expiry(datetime): time up to which link is valid.
        type(int): type indicating the event associated.
    """

    user = models.ForeignKey(
        FairfoodUser,
        on_delete=models.CASCADE,
        related_name="validation_tokens",
    )
    key = models.CharField(default="", max_length=200, blank=True)
    status = models.IntegerField(
        default=VTOKEN_STATUS_UNUSED, choices=VTOKEN_STATUS_CHOICES
    )
    expiry = models.DateTimeField(default=timezone.now)
    type = models.IntegerField(default=1, choices=VTOKEN_TYPE_CHOICES)

    request_data = fields.JSONField(null=True, blank=True)

    def __str__(self):
        """Object name in django admin."""
        return f"{self.user.name}:{self.key}:{self.pk}"

    def save(self, *args, **kwargs):
        """Overriding the default save signal.

        This function will generate the token key based on the type of
        the token and save when the save() function is called if the key
        is empty. It. will. also set the expiry when the object is
        created for the first time.
        """
        if not self.key:
            self.key = self.generate_unique_key()
        if not self.id:
            self.expiry = self.get_expiry()
        return super(ValidationToken, self).save(*args, **kwargs)

    def get_validity_period(self):
        """To perform function get_validity_period."""
        return TOKEN_VALIDITY[self.type]

    def get_expiry(self):
        """To get the validity based on type."""
        validity = self.get_validity_period()
        return timezone.now() + timedelta(minutes=validity)

    def generate_unique_key(self):
        """To generate unique key."""
        if self.type != VTOKEN_TYPE_OTP:
            key = get_random_string(settings.ACCESS_TOKEN_LENGTH)
        else:
            # Removed complicated chars
            allowed_chars = "ABCDEGHJKLMNPRSTUVWXYZ2345689"
            key = get_random_string(
                settings.OTP_LENGTH, allowed_chars=allowed_chars
            )

        if ValidationToken.objects.filter(
            key=key, type=self.type, status=VTOKEN_STATUS_UNUSED
        ).exists():
            key = self.generate_unique_key()
        return key

    def validate(self):
        """To.

        validate the token.
        """
        status = True
        if not self.is_valid:
            status = False
        self.status = VTOKEN_STATUS_USED
        self.updater = self.user
        self.save()
        return status

    def send_otp(self):
        """To send OTP to citizen."""
        if (
            self.is_valid
            and self.user.type == USER_TYPE_NODE_USER
            and (self.type == VTOKEN_TYPE_OTP)
        ):
            mobile = self.user.username
            message = MESSAGE_USER_OTP % (self.key, self.get_validity_period())
            vendors.send_sms(mobile, message)
        return True

    def refresh(self):
        """Function  to refresh the validation token."""
        if not self.is_valid:
            self.key = self.generate_unique_key()
            self.status = VTOKEN_STATUS_UNUSED
        self.expiry = self.get_expiry()
        self.updater = self.user
        self.save()
        return True

    def mark_as_used(self):
        """To mark validation token as used."""
        self.status = VTOKEN_STATUS_USED
        self.save()

    @staticmethod
    def initialize(user, type, creator=None):
        """To initialize verification."""
        creator = creator if creator else user
        token, created = ValidationToken.objects.get_or_create(
            user=user, status=VTOKEN_STATUS_UNUSED, type=type, creator=creator
        )
        if not created:
            token.refresh()
        return token

    @property
    def validity(self):
        """To get the validity of token."""
        return _date_time_desc(self.expiry)

    @property
    def created_on_desc(self):
        """To get the validity of token."""
        return _date_time_desc(self.created_on)

    @property
    def is_valid(self):
        """Function  which check if Validator is valid."""
        if self.expiry > timezone.now() and (
            self.status == VTOKEN_STATUS_UNUSED
        ):
            return True
        return False

    def invalidate(self):
        """To perform function invalidate."""
        self.mark_as_used()
        self.expiry = timezone.now()
        self.save()
        return True


class AccessToken(models.Model):
    """The default authorization token model.

    This model is overriding the DRF token
    Attribs:
        user(obj): user object
        Key(str): token
        created(datetime): created date and time.
        device(obj): device object
    """

    user = models.ForeignKey(
        FairfoodUser, related_name="auth_token", on_delete=models.CASCADE
    )
    key = models.CharField(max_length=200, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    device = models.ForeignKey(
        "accounts.UserDevice", on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        """To return value in django admin."""
        return self.key

    def save(self, *args, **kwargs):
        """Overriding the save method to generate key."""
        if not self.key:
            self.key = self.generate_unique_key()
        return super(AccessToken, self).save(*args, **kwargs)

    def generate_unique_key(self):
        """To generate unique key."""
        key = get_random_string(settings.ACCESS_TOKEN_LENGTH)
        if AccessToken.objects.filter(key=key).exists():
            self.generate_unique_key()
        return key

    def refresh(self):
        """Function  to change token."""
        self.key = self.generate_unique_key()
        self.save()
        return self.key


class UserDevice(AbstractFCMDevice, AbstractBaseModel):
    """Class for user devices.

    This is inherited from the AbstractFCMDevice and
    AbstractBaseModel.

    Attribs:
        user(obj): user object.
        type(int): device types
    Attribs Inherited:
        name(str): name of the device
        active(bool): bool value.
        date_created(datetime): created time.
        device_id(str): Device id
        registration_id(str): Reg id
    """

    user = models.ForeignKey(FairfoodUser, on_delete=models.CASCADE)
    type = models.IntegerField(
        default=DEVICE_TYPE_ANDROID, choices=DEVICE_TYPE_CHOICESS
    )
    registration_id = models.TextField(
        verbose_name="Registration token", blank=True, default=""
    )

    class Meta:
        """Meta data."""

        verbose_name = "User device"
        verbose_name_plural = "User devices"

    def activate(self, types=MOBILE_DEVICE_TYPES):
        """Function for set device as active and set other devices of same user
        as inactive."""
        for device in UserDevice.objects.filter(
            user=self.user, type__in=types
        ):
            if device.active:
                device.active = False
                device.updater = self.user
                device.save()
        self.active = True
        self.save()
        return True

    def generate_token(self, force_create=False, refresh=True) -> dict:
        """Function to create a unique token for a device.

        This function will create a token for the device if force create is
        true or retrieve the existing token and refresh it

        refresh: refresh on each login, or just get or create token on
        each login
        """
        response = {"is_granted": True, "token": ""}
        if not force_create:
            try:
                token = AccessToken.objects.get(
                    device=self, user=self.user, device__active=True
                )
                # refresh token only if refresh is True.
                response["token"] = (
                    token.key if not refresh else token.refresh()
                )
            except Exception as exc:
                expected = (ObjectDoesNotExist, MultipleObjectsReturned)
                if not isinstance(exc, expected):
                    raise exc
                token_exists = AccessToken.objects.filter(
                    user=self.user, device__active=True
                ).exists()
                # new token will be issued if not refresh enabled.
                if not token_exists or not refresh:
                    response["token"] = self.user.issue_access_token(self)
                else:
                    response["is_granted"] = False
                    return response

            self.user.last_login = timezone.now()
            self.user.save()
            return response

        old_mobile_tokens = AccessToken.objects.filter(
            user=self.user, device__type__in=MOBILE_DEVICE_TYPES
        )
        old_mobile_tokens.delete()
        response["token"] = self.user.issue_access_token(self)
        return response


class TermsAndConditions(AbstractBaseModel):
    """
    Model to store different versions of terms and conditions
    Attributes:
        title(str)      : Title of Terms & Conditions
        version(int)    : Version of Terms & Conditions
    """

    title = models.CharField(max_length=100, null=True, blank=True)
    version = models.CharField(max_length=20)
    default = models.BooleanField(default=False)

    def __str__(self):
        """To perform function __str__."""
        return f"V{self.version} - {self.title})"

    def make_default(self):
        """To perform function make_default."""
        for tc in TermsAndConditions.objects.all():
            tc.default = False
            tc.save()
        self.default = True
        self.save()


class UserTCAcceptance(AbstractBaseModel):
    """
    Model to store details and proof of user's acceptance of terms and
    conditions
    Attributes:
        user(obj)   : User who accepted the T&C
        tc(obj)     : Terms & conditions that the user accepted
        ip(str)     : IP Address from which the user accepted the terms
    """

    user = models.ForeignKey(FairfoodUser, on_delete=models.CASCADE)
    tc = models.ForeignKey(TermsAndConditions, on_delete=models.CASCADE)
    ip = models.CharField(max_length=50, null=True, blank=True)


class ClientVersion(AbstractBaseModel):
    """Model to store the details about client versions.

    Attributes:
        name(str)               : Name of version.
        client(int)             : Type of client where web or app.
        release_date(datetime)  : Release date of version.
        last_active(datetime)   : last active date of version.
    """

    name = models.CharField(max_length=100, default="", null=True, blank=True)
    client = models.IntegerField(
        default=trans_constants.CLIENT_WEB,
        choices=trans_constants.CLIENT_CHOICES,
    )
    release_date = models.DateTimeField(blank=True, null=True)
    last_active = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.name} - {self.get_client_display()}"


class UserClientVersion(AbstractBaseModel):
    """Model to store the details about currently which version is using by the
    user.

    Attributes:
        user(obj)              : User object.
        version(obj)           : Version object.
        last_active(datetime)  : last active date of user version.
    """

    user = models.ForeignKey(
        "accounts.FairfoodUser",
        on_delete=models.CASCADE,
        related_name="user_versions",
    )
    version = models.ForeignKey(ClientVersion, on_delete=models.CASCADE)
    last_active = models.DateTimeField(blank=True, null=True)

    objects = UserClientVersionQuerySet.as_manager()

    def __str__(self):
        """To perform function __str__."""
        return f"{self.user.name} - {self.version}"
