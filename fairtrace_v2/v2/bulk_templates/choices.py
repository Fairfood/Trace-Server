"""Choices used in the app bulk_templates."""
import enum


# class Validator():
#     """
#
#     """
#
#     def __init__(self, value, field=None):
#         self.min = None
#         self.max = None
#         self.value = value
#         self.field = field
#         func_name = self.field
#         func = getattr(self, func_name)
#         func()
#
#     def integer(self):
#         re_decimal = re.compile(r'\.0*\s*$')
#         try:
#             self.value = int(re_decimal.sub('', str(self.value)))
#         except Exception:
#             raise ValidationError('should be an integer')
#         return self.value
#
#     def float(self):
#         try:
#             self.value = float(self.value)
#         except Exception:
#             raise ValidationError('should be an float')
#         return self.value
#
#     def character(self):
#         if not isinstance(self.value, (str,)):
#             raise ValidationError('should be a character')
#         return self.value
#
#     def date(self):
#         if isinstance(self.value, datetime.datetime):
#             raise ValidationError('should be a character')
#         supported_formats = (
#             "%d-%m-%Y", '%d/%m/%Y', "%d-%m-%y", '%d/%m/%y')
#         for fmt in supported_formats:
#             try:
#                 value = datetime.datetime.strptime(
#                     str(self.value), fmt)
#                 if value is not None:
#                     return value
#                 break
#             except Exception:
#                 pass
#         raise ValidationError('should be in date format')
#
#     def email(self):
#         if self.value:
#             try:
#                 self.value = validate_email(self.value)
#             except Exception:
#                 raise ValidationError("should be in email format")
#             return self.value
#
#     def phone(self):
#         """ Raise a ValidationError if the value looks like a
#         mobile telephone number.
#         """
#         if self.value:
#             self.value = str(self.value).replace(' ', '')
#             self.value = str(self.value).replace('-', '')
#             try:
#                 self.value = int(self.value)
#             except Exception:
#                 raise ValidationError("Invalid mobile number.")
#         return self.value
#
#     def latitude(self):
#         self.min = -90
#         self.max = 90
#         if self.min <= self.value <= self.max:
#             return self.value
#         raise ValidationError('value between -90 and 90')
#
#     def longitude(self):
#         self.min = -180
#         self.max = 180
#         if self.min <= self.value <= self.max:
#             return self.value
#         raise ValidationError('value between -180 and 180')


# class FieldType(MultiValueEnum):
#     """
#     Template Type method choices.
#
#     The function that is supposed to be called is also
#     listed in the constants.
#     """
#
#     _init_ = 'value validator'
#     INTEGER = 1, 'integer'
#     FLOAT = 2,  'float'
#     CHARACTER = 3,  'character'
#     DATE = 4, 'date'
#     EMAIL = 5, 'email'
#     PHONE = 6, 'phone'
#     LATITUDE = 7, 'latitude'
#     LONGITUDE = 8, 'longitude'


@enum.unique
class FieldType(enum.IntEnum):
    """FieldType choices."""

    FARMER_ID = 1
    LATITUDE = 2
    STRING = 3
    INTEGER = 4
    FLOAT = 5
    DATE = 6
    PHONE = 7
    EMAIL = 8
    TRACE_ID = 9
    CURRENCY = 10
    UNIT = 11
