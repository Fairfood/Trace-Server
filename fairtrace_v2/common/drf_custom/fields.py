"""All custom used fields are declared here."""
import decimal
import json

from common.library import _decode
from common.library import _encode
from common.library import _split_phone
from common.library import _unix_to_datetime
from common.library import _validate_password
from common.library import _validate_phone
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_text
from django.utils.formats import sanitize_separators
from openpyxl import load_workbook
from rest_framework import serializers


# from django.contrib.auth.hashers import make_password


class UnixTimeField(serializers.DateTimeField):
    """Custom field to accept Unix time stamp in date time field."""

    def to_internal_value(self, data):
        """To convert date time from Unix."""
        return _unix_to_datetime(data)


class PasswordField(serializers.CharField):
    """Custom field for password."""

    write_only = True
    allow_null = False

    def to_internal_value(self, value):
        """Validator to validate password."""
        valid, messages = _validate_password(value)
        if not (valid):
            raise serializers.ValidationError(messages)
        return value


class PhoneNumberField(serializers.CharField):
    """Custom field for phone number.

    Input can be in any of the formats
        - dict {'dial_code':'+1', 'phone':'81818181818'}
        - list ['+1', '81818181818']
        - tuple ('+1', '81818181818')
        - str '+181818181818'
    Output can be formatted as a dict, list or str.

    The format is by default a dict.
    """

    output_format = dict  # Supports dict, str or list
    supported_formats = [str, list, dict]

    def __init__(self, output_format=dict, **kwargs):
        """Initializing PhoneNumberField object, to set output_format."""
        if output_format not in self.supported_formats:
            raise ValueError(
                "output_format not supported. It should be either dict, str or"
                " list."
            )
        self.output_format = output_format
        super(PhoneNumberField, self).__init__(**kwargs)

    def format(self, code, phone):
        """Function to format the output according to specified output
        format."""
        if self.output_format == dict:
            phone_number = {"dial_code": code, "phone": phone}
        elif self.output_format == list:
            phone_number = [code, phone]
        else:
            phone_number = "%s%s" % (code, phone)
        return phone_number

    def to_internal_value(self, value):
        """Validator to validate phone."""
        if type(value) == dict:
            if (
                not value["dial_code"] or not value["phone"]
            ) and self.allow_blank:
                return ""

            if "dial_code" not in value.keys() or "phone" not in value.keys():
                raise serializers.ValidationError(
                    "Dial code and phone number is required"
                )
            phone = "%s%s" % (value["dial_code"], value["phone"])
        elif type(value) == str:
            phone = value
        elif type(value) in [tuple, list]:
            phone = "".join(value)
        else:
            raise serializers.ValidationError(
                "Un-supported phone number format"
            )

        if not phone and self.allow_blank:
            return ""

        if not phone.startswith("+"):
            phone = "+%s" % phone
        phone = _validate_phone(phone)
        if not phone:
            raise serializers.ValidationError(
                "Invalid phone number/country code"
            )
        return phone

    def to_representation(self, value):
        """Validator to validate phone."""
        code, phone = _split_phone(value)
        return self.format(code, phone)


class CharListField(serializers.CharField):
    """Custom field for character list field."""

    child = serializers.CharField()

    def to_representation(self, value):
        """Validator to validate phone."""
        try:
            return eval(value)
        except Exception:
            return value

    def to_internal_value(self, value):
        """Validator to validate phone."""
        try:
            return eval(value)
        except Exception:
            return value


class JsonField(serializers.CharField):
    """Custom field for character list field."""

    child = serializers.CharField()

    def to_representation(self, value):
        """Validator to validate phone."""
        try:
            return json.loads(value)
        except Exception:
            return value

    def to_internal_value(self, value):
        """Validator to validate phone."""
        try:
            return json.dumps(value)
        except Exception:
            return value


class IdencodeField(serializers.CharField):
    """Encoded id field."""

    serializer = None
    related_model = None

    def __init__(self, serializer=None, related_model=None, *args, **kwargs):
        """Initializing field object."""
        self.serializer = serializer
        self.related_model = related_model
        super(IdencodeField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        """Override the returning method.

        This function will check if the serializer is supplied in case
        of foreign key field. In case of foreign key, the value will be
        and object. If it is  normal id then it is going to be type int.
        """
        if not value:
            return None
        if self.serializer:
            return self.serializer(value).data
        if isinstance(value, int):
            return _encode(value)
        try:
            return _encode(value.id)
        except Exception:
            return None

    def to_internal_value(self, value):
        """To convert value for saving."""
        initial_value = value

        if not value:
            return value

        if self.related_model and isinstance(value, self.related_model):
            return value
        try:
            value = _decode(value) or int(value)
        except Exception:
            value = float("-inf")
        if not value:
            raise serializers.ValidationError("Invalid id/pk format")
        related_model = self.related_model
        if not related_model:
            try:
                related_model = self.parent.Meta.model._meta.get_field(
                    self.source
                ).related_model
            except Exception:
                raise serializers.ValidationError(
                    "Invalid key, the key should be same as the model. "
                )
        try:
            return related_model.objects.get(id=value)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                "Invalid pk - object does not exist."
            )
        except OverflowError:
            return initial_value


class ManyToManyIdencodeField(serializers.CharField):
    """Encoded id field."""

    serializer = None
    related_model = None

    def __init__(self, serializer=None, related_model=None, *args, **kwargs):
        """Initializing field object."""
        self.serializer = serializer
        self.related_model = related_model
        super(ManyToManyIdencodeField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        """Override the returning method.

        This function will check if the serializer is supplied in case
        of foreign key field. In case of foreign key, the value will be
        and object. If it is  normal id then it is going to be type int.
        """
        if not value:
            return []
        if self.serializer:
            data = []
            for pk in value.all():
                data.append(self.serializer(pk).data)
            return data
        data = []
        for item in value.all():
            if isinstance(item, int):
                data.append(_encode(item))
            try:
                data.append(_encode(item.id))
            except Exception:
                return []
        return data

    def to_internal_value(self, value):
        """To convert value for saving."""
        data = []
        if value is None:
            values = []
        elif type(value) == str:
            values = [i.strip() for i in value.split(",")]
        elif type(value) == list:
            values = value
        else:
            raise serializers.ValidationError("Should be list of IDs")
        for pk in values:
            try:
                data.append(int(pk))
            except Exception:
                data.append(_decode(pk))
        related_model = self.related_model
        if not related_model:
            try:
                related_model = self.parent.Meta.model._meta.get_field(
                    self.source
                ).related_model
            except Exception:
                raise serializers.ValidationError(
                    "Invalid key, the key should be same as the model. "
                )
        try:
            return related_model.objects.filter(id__in=data)
        except Exception:
            raise serializers.ValidationError(
                "Invalid pk - object does not exist."
            )


class RemovableImageField(serializers.ImageField, serializers.CharField):
    """DRF does not give you an option to remove an image, Since emtpy values
    are not accepted by the ImageField.

    However, if an empty value is passed for the field in serializer
    update, the image id correctly removed. This field does just that
    """

    def to_internal_value(self, data):
        """Return emtpy string if input is an empty string."""
        if not data:
            return data
        return super(serializers.ImageField, self).to_internal_value(data)


class BulkTemplateField(serializers.FileField):
    """Helper class to build excel bulk template fields."""

    excel_template = None

    def __init__(self, excel_template, *args, **kwargs):
        """To perform function __init__."""
        super(BulkTemplateField, self).__init__(*args, **kwargs)
        self.excel_template = excel_template

    def to_internal_value(self, data):
        """Value to be saved."""
        file = super(BulkTemplateField, self).to_internal_value(data)

        wb = load_workbook(file, data_only=True)
        excel = self.excel_template(workbook=wb)
        return excel.validate()


class KWArgsObjectField(serializers.Field):
    """Encoded id field."""

    serializer = None
    related_model = None

    def __init__(self, serializer=None, related_model=None, *args, **kwargs):
        """Initializing field object."""
        self.serializer = serializer
        self.related_model = related_model
        super(KWArgsObjectField, self).__init__(*args, **kwargs)

    def get_value(self, dictionary):
        """Overriding the get value of the serializer field."""
        try:
            try:
                return self.context["view"].kwargs[self.field_name]
            except Exception:
                return self.context[self.field_name]
        except Exception:
            # returning original value as fail-safe.
            return super().get_value(dictionary)

    def to_representation(self, value):
        """Override the returning method.

        This function will check if the serializer is supplied in case
        of foreign key field. In case of foreign key, the value will be
        and object. If it is  normal id then it is going to be type int.
        """
        if not value:
            return None
        if self.serializer:
            try:
                return self.serializer(value).data
            except Exception:
                print("except")
                pass
        if isinstance(value, int):
            return _encode(value)
        try:
            return _encode(value.id)
        except Exception:
            return None

    def to_internal_value(self, value):
        """To convert value for saving."""
        return value


class RequestIPField(serializers.Field):
    """Encoded id field."""

    def get_value(self, dictionary):
        """Function wil get the user's IP address from the request."""
        try:
            ip = self.context["request"].META.get("REMOTE_ADDR")
            x_forwarded_for = self.context["request"].META.get(
                "HTTP_X_FORWARDED_FOR"
            )
            if not ip and x_forwarded_for:
                ip = x_forwarded_for.split(",")[0]
            return ip
        except Exception:
            if self.required:
                raise serializers.ValidationError("IP not found")

    def to_internal_value(self, value):
        """To convert value for saving."""
        return value


class NullableFileField(serializers.FileField):
    """File field that can be set to None."""

    def to_internal_value(self, data):
        """To convert value for saving."""
        data = None if type(data) == str and data == "null" else data
        if data is None and self.allow_null and not self.required:
            return None
        return super(NullableFileField, self).to_internal_value(data)


class RoundingDecimalField(serializers.DecimalField):
    """A decimal field that will automatically round to the specified decimal
    place."""

    @staticmethod
    def round_decimal(value, places):
        """Rounding decimal."""
        if value is not None:
            # see https://docs.python.org/2/library/decimal.html#decimal
            # .Decimal.quantize for options
            return value.quantize(decimal.Decimal(10) ** -places)
        return value

    def to_internal_value(self, data):
        """To convert value for saving."""
        data = smart_text(data).strip()

        if self.localize:
            data = sanitize_separators(data)

        if len(data) > self.MAX_STRING_LENGTH:
            self.fail("max_string_length")

        try:
            value = decimal.Decimal(data)
        except decimal.DecimalException:
            self.fail("invalid")

        # Check for NaN. It is the only value that isn't equal to itself,
        # so we can use this to identify NaN values.
        if value != value:
            self.fail("invalid")

        # Check for infinity and negative infinity.
        if value in (decimal.Decimal("Inf"), decimal.Decimal("-Inf")):
            self.fail("invalid")

        value = self.round_decimal(value, self.decimal_places)

        return self.quantize(self.validate_precision(value))


class ListRepresentationField(serializers.ListField):
    """Custom field for character list field."""

    child = serializers.CharField()

    def to_representation(self, value):
        """To convert value for representation."""
        return super().to_representation(value.split(","))

    def to_internal_value(self, value):
        """To convert value for saving."""
        return ",".join(super().to_internal_value(value))


class RelatedIdencodeField(serializers.PrimaryKeyRelatedField):
    """Class to handle RelatedIdencodeField and functions."""

    def to_representation(self, value):
        """To perform function to_representation."""
        value = super().to_representation(value)
        return _encode(value)

    def to_internal_value(self, data):
        """To perform function to_internal_value."""
        data = _decode(data)
        return super().to_internal_value(data)
