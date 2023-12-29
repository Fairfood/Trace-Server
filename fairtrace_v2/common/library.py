"""Commonly used helper function are defined here."""
import ast
import binascii
import hashlib
import io
import json
import string
from collections import OrderedDict
from datetime import datetime
from random import randint
from random import random
from time import mktime
from time import time

import phonenumbers
import requests
from Crypto.Cipher import AES
from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.core.validators import validate_email
from django.db.models import Sum
from django.db.models.expressions import RawSQL
from django.utils import translation
from django.utils.crypto import get_random_string
from django.utils.timezone import localtime
from django.utils.translation import gettext as _
from hashids import Hashids
from pytz import timezone
from rest_framework import status
from rest_framework.response import Response
from tabulate import tabulate

from .exceptions import BadRequest

prev_time_log = int(time() * 100000)
prev_stage = ""
stage_times = {}
stage_count = {}


class DateTimeEncoder(json.JSONEncoder):
    """Class to encode datetime."""

    def default(self, o):
        """To encode datetime."""
        if isinstance(o, datetime):
            return o.isoformat()


def _reset_time_stages():
    """To perform function _reset_time_stages."""
    global prev_time_log
    global stage_times
    global prev_stage
    global stage_count
    stage_times = {}
    stage_count = {}
    prev_stage = ""


def _time_since(stage="", intend=0):
    """Module to debug delays in execution times.

    Call this function at stags where you need to check the time, and it will
    print the time since the function was previously called.
    Args:
        stage: Optional message to append before the time

    Returns: time in seconds
    """
    global prev_time_log
    global stage_times
    global prev_stage
    global stage_count

    current_time = int(time() * 100000)
    time_since = current_time - prev_time_log
    prev_time_log = current_time
    if not stage:
        return time_since, stage_times, stage_count
    if prev_stage in stage_times:
        stage_times[prev_stage] += time_since
    else:
        stage_times[prev_stage] = time_since
    if stage in stage_count:
        stage_count[stage] += 1
    else:
        stage_count[stage] = 1

    print("\t" * intend, stage, time_since)
    prev_stage = stage
    return time_since, stage_times, stage_count


def _end_time_stages():
    """To perform function _end_time_stages."""
    time_diff, total, count = _time_since("Ending & sorting")
    total.pop("", None)
    count.pop("", None)
    total_time = sum(total.values())
    percentage = {i: (j / total_time) * 100 for i, j in total.items()}

    table = [(percentage[i], i, total[i], count[i]) for i in percentage.keys()]
    table = sorted(table, reverse=True)
    print(tabulate(table, headers=["Percentage", "Stage", "Time", "Count"]))

    _time_since("Returning and resetting timer")


def _get_location_from_ip(ip):
    """Module to get location from IP.

    Input Params:
        ip(str): ip address of user.
    Returns:
        (str): location
    """
    try:
        address = ""
        location = json.loads(requests.get(settings.GEO_IP_URL + ip).content)
        if location["city"]:
            address = location["city"] + ", "
        if location["region_name"]:
            address += location["region_name"] + ", "
        if location["country_name"]:
            address += location["country_name"]

        if address:
            return address
    except Exception:
        return "Unknown Location"


def _generate_random_number(digits):
    """Function to generate n dig random number.

    Input Params:
        digits(int): number of digits
    Returns:
        (int): number
    """
    range_start = 10 ** (digits - 1)
    range_end = (10 ** digits) - 1
    return randint(range_start, range_end)


def _pop_out_from_dictionary(dictionary, keys):
    """Function to remove keys from dictionary.

    Input Params:
        dictionary(dict): dictionary
        keys(list)
    Returns:
        dictionary(dictionary): updated dictionary.
    """
    for key in keys:
        dictionary.pop(key, None)
    return dictionary


def _success_response(data=None, message=None, status=status.HTTP_200_OK):
    """Function to create success Response.

    This function will create the standardized success response.
    """
    data = data if data else {}
    response = {
        "success": True,
        "detail": message,
        "code": status,
        "data": data,
    }
    if not message:
        response["detail"] = "Success."
    return Response(response, status=status)


def success_response(data=None, message=None, status=status.HTTP_200_OK):
    """To perform function success_response."""
    return _success_response(data=data, message=message, status=status)


def _validate_phone(number):
    """Function to validate phone number.

    Input Params:
        number(str): international phone number
    Returns:
        dictionary with
        phone(str): phone number
        code(str): country code
    """
    try:
        number = number.replace(" ", "")
        number = number.replace("-", "")
        number = phonenumbers.parse(number)
        phone = str(number.national_number)
        code = "+" + str(number.country_code)
        return code + phone
    except Exception:
        return None


def split_phone(number):
    """
    A public function.

    To perform function split_phone. This function will split the phone number
    into dial code and phone number.
    """
    return _split_phone(number)


def _split_phone(number):
    """Function to split phone number into dial code and phone number.

    Args:
        number: concatenated phone number
    Returns:
        dial_code: International dialing code
        phone: National phone number.
    """
    number = number.replace(" ", "")
    number = number.replace("-", "")
    try:
        number = phonenumbers.parse(number)
        phone = str(number.national_number)
        code = "+" + str(number.country_code)
        return code, phone
    except Exception:
        if "+" in number and len(number) < 4:
            return number, ""
        return "", number.replace("+", "")


def _convert_to_timestamp(date):
    """To convert Unix timestamps to date time."""
    try:
        unix = mktime(date.timetuple())
    except Exception:
        unix = 0.0

    return unix


def _validate_password(password):
    """Function to validate password.

    Input Params:
        password(str): password.
    Returns:
        valid(bool): valid status.
        message(str): validity message.
    """
    try:
        password_validation.validate_password(password)
        valid = True
        message = "Valid Password."
    except ValidationError as e:
        valid = False
        message = "; ".join(e.messages)
    return (valid, message)


def _validate_email(email):
    """To validate email address."""
    try:
        validate_email(email)
        return (True, "Valid Email address.")
    except ValidationError as e:
        message = "; ".join(e.messages)
        return (False, message)


def _unix_to_datetime(unix_time):
    """To convert Unix timestamps to date time."""
    try:
        unix_time = float(unix_time)
        localtz = timezone(settings.TIME_ZONE)
        date = localtz.localize(datetime.fromtimestamp(unix_time))
        return date
    except Exception:
        raise BadRequest("Unix timestamps must be float or int")


def unix_to_datetime(unix_time):
    """Making method public."""
    return _unix_to_datetime(unix_time)


def _datetime_to_unix(date):
    """To convert Unix timestamps to date time."""
    try:
        unix = mktime(date.timetuple())
    except Exception:
        unix = 0.0

    return unix


def _encode(value):
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


def hash_dict(dictionary):
    """Function to hash dictionary.

    Input Params:
        dictionary(dict): dictionary
    Returns:
        hashed string.
    """
    json_str = json.dumps(dictionary, cls=DateTimeEncoder, sort_keys=True)

    hash_value = hashlib.sha256(json_str.encode()).hexdigest()
    return hash_value


def encode(value):
    """Making function public."""
    return _encode(value)


def _decode(value):
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


def decode(value):
    """Making function public."""
    return _decode(value)


def _date_time_desc(date):
    """To format date time."""
    try:
        date = localtime(date)
    except Exception:
        pass
    date = date.strftime("%d %B %Y, %H:%M %p")
    date += ", Timezone: %s" % settings.TIME_ZONE
    return date


def _gcd_get_raw_sql_distance(latitude, longitude, max_distance=None):
    """Function to create raw SQL distance with GCD.

    This function will compute raw SQL distance with
    Great circle distance formula.
    Input Params:
        latitude(float): reference location latitude.
        longitude(float): reference location longitude
        max_distance(float): max distance in KM
    Returns:
        (obj): distance in raw SQL object.
    """
    gcd_formula = (
        "6371 * acos(least(greatest(        cos(radians(%s)) *"
        " cos(radians(latitude))         * cos(radians(longitude) -"
        " radians(%s)) +         sin(radians(%s)) * sin(radians(latitude))    "
        "     , -1), 1))"
    )
    distance_raw_sql = RawSQL(gcd_formula, (latitude, longitude, latitude))
    return distance_raw_sql


def _encrypt(message):
    """To encrypt a message."""
    iv = str.encode(settings.SECRET_KEY[-16:])
    key = str.encode(settings.SECRET_KEY[:16])
    cipher = AES.new(key, AES.MODE_CFB, iv)
    msg = cipher.encrypt(str.encode(message))
    return binascii.hexlify(msg).decode("utf-8")


def _decrypt(code):
    """To decrypt the message."""
    iv = str.encode(settings.SECRET_KEY[-16:])
    key = str.encode(settings.SECRET_KEY[:16])
    cipher = AES.new(key, AES.MODE_CFB, iv)
    code = binascii.unhexlify(code)
    message = cipher.decrypt(code)
    return message.decode("utf-8")


def _decode_list(items):
    """To decode a list of items."""
    if type(items) != list:
        return []
    data = []
    for item in items:
        item = _decode(item)
        if item:
            data.append(item)
    return data


def _anonymise_email(email):
    """To get anonymity email."""
    email = str(email)
    if len(email) < 4:
        return "******"
    try:
        name = email.split("@")[0]
        privider = email.split("@")[1].split(".")[0]
        doamin = email.split("@")[1].split(".")[1]
        value = name[0:2] + "*******@" + privider[0] + "**" + doamin
    except Exception:
        value = email[0:2] + "*****" + email[-2:]
    return value


def _anonymise_value(value):
    """To get anonymity value."""
    value = str(value)
    if len(value) < 4:
        return "******"
    return "*****" + value[-4:]


def _is_image_valid(image):
    """To check the image is valid."""
    valid = image.name.lower().endswith(
        (
            ".bmp",
            ".dib",
            ".gif",
            ".tif",
            ".tiff",
            ".jfif",
            ".jpe",
            ".jpg",
            ".jpeg",
            ".pbm",
            ".pgm",
            ".ppm",
            ".pnm",
            ".png",
            ".apng",
            ".blp",
        )
    )
    if valid:
        return True
    return False
    # try:
    #     print ('verifying')
    #     image = Image.open(image)
    #     image.verify()
    #     image.close()
    #     print ('success _is_image_valid')
    #     return True
    # except Exception:
    #     return False


def _convert_blob_to_image(blob):
    """To convert blob to image file."""
    try:
        with io.BytesIO(blob) as stream:
            file = File(stream)
        return file
    except Exception:
        return None


def _strlist_to_list(value):
    """To convert string list to list."""
    try:
        value = ast.literal_eval(value)
        if not isinstance(value, list):
            return None
        return value
    except Exception:
        return None


def _list_to_sentence(word_list):
    """To convert list to sentence."""
    word_list = list(map(str, word_list))
    if not word_list[:-1]:
        return " ".join(word_list)
    return "%s %s %s" % (", ".join(word_list[:-1]), _("and"), word_list[-1])


def _get_file_path(instance, filename):
    """
    Function to get filepath for a file to be uploaded
    Args:
        instance: instance of the file object
        filename: uploaded filename

    Returns:
        path: Path of file
    """
    type = instance.__class__.__name__.lower()
    path = "%s/%s/%s:%s" % (type, instance.id, get_random_string(10), filename)
    return path


def get_file_path_without_random(instance, filename):
    """To perform function get_file_path_without_random."""
    _type = instance.__class__.__name__.lower()
    return f"{_type}/{instance.idencode}/{filename}"


def _percentage(value, total):
    """
    Calculates the percentage without zerodivision error.
    If total is 0. returns 0 without raising error.
    Args:
        value: Value to convert to percentage
        total: Total value

    Returns:
        percentage: Percentage
    """
    try:
        return round((float(value) / float(total)) * 100, 2)
    except ZeroDivisionError:
        return 0


def _safe_append_to_dict_key(dictionary, key, value):
    """
    Appends a value to the list in the key of a dict without raising keyerror
    Args:
        dictionary: dict to append to
        key: key containing the list
        value: value to be appended

    Returns:
        dictionary: updated dict
    """

    try:
        dictionary[key].append(value)
    except KeyError:
        dictionary[key] = [value]
    return dictionary


def _safe_join_to_query(dictionary, key, query):
    """Append a query to an existing query in the key of a dict without raising
    keyerror Args: dictionary: dict to append to key: key containing the query
    query: query to be appended.

    Returns:
        dictionary: updated dict
    """

    try:
        dictionary[key] = _combine_queries(dictionary[key], query)
    except KeyError:
        dictionary[key] = query
    return dictionary


def _pseudonymize_data(field, data):
    """
    Function to pseudonymize data
    Args:
        data: Input data

    Returns:
        data: Pseudonymized data
    """
    if not data:
        return data
    data_type = type(data)
    if data_type == str:
        if field in ["name", "first_name"]:
            return "Anonymous"
        elif field in ["last_name", "dial_code"]:
            return ""
        else:
            return "Anonymized"
    if data_type == list:
        return [_pseudonymize_data(i, field) for i in data]
    if data_type == dict or data_type == OrderedDict:
        return {k: _pseudonymize_data(k, v) for k, v in data.items()}
    if data_type == int:
        return 999999
    if data_type == float:
        sign = (-1) ** randint(1, 2)
        return sign * data * random()
    return data


def _update_list_of_dict(existing_dict, new_items, unique_key="id"):
    """
    Function to update a list of dict with new items, and remove duplicate
    based on a key.
    Args:
        existing_dict: List to be updated.
        new_items: New items to be added.
        unique_key: The dict key that should be used to check unique.

    Returns:
        updated_dict
    """
    existing_dict += new_items
    updated_dict = list({v[unique_key]: v for v in existing_dict}.values())
    return updated_dict


def _combine_queries(first_query, second_query):
    """Function to combine two queries.

    The following code looks stupid. But it kept getting an AssertionError
    when trying to combine two querysets. I was able to narrow down the
    cause and understood that the error is caused when you try to combine
    two queryset in which the first one has a count of 0 or 1.

    References:
    https://code.djangoproject.com/ticket/24525
    https://code.djangoproject.com/ticket/26522
    https://code.djangoproject.com/ticket/26959
    """
    assert (
            first_query.model == second_query.model
    ), "Cannot combine queries of two models"
    QueryModel = first_query.model

    try:
        combined = first_query | second_query
    except AssertionError:
        try:
            combined = second_query | first_query
        except AssertionError:
            sup_ids = [i.id for i in first_query]
            buy_ids = [i.id for i in second_query]
            combined = QueryModel.objects.filter(
                id__in=sup_ids + buy_ids
            ).distinct("id")
    return combined


def _query_sum(query, key, round_off=True):
    """To calculate the sum of a query set."""
    total = query.aggregate(total=Sum(key))["total"]
    if not total:
        return 0.0
    if round_off:
        return round(float(total))
    return total


def query_sum(query, key, round_off=True):
    """To calculate the sum of a query set.

    Note: This is a public function.
    """
    return _query_sum(query, key, round_off=True)


def _hash_file(file):
    """Function to compute the hash of a file.

    Args:
        file: file to be hashed.
        block_size: fixed block size

    Returns:
    """
    if not file:
        return ""
    md5 = hashlib.md5()
    for chunk in file.chunks():
        md5.update(chunk)
    return md5.hexdigest()


def hash_file(file):
    """Function to compute the hash of a file."""
    return _hash_file(file)


def _translate(string, language):
    """To translate string."""
    translation.activate(language)
    content = _(string)
    translation.deactivate()
    return content


def get_acronym(text):
    """Function to convert text to short form."""
    acronym = ". ".join(word[0] for word in text.split())
    return acronym.upper()


def _string_to_datetime(date):
    """To convert string to date time."""
    try:
        date = datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m-%d")
    except Exception:
        date = datetime.strptime("1-1-1970", "%d-%m-%Y").strftime("%Y-%m-%d")
    return date


def convert_float(value):
    """To perform function convert_float."""
    try:
        return float(value)
    except Exception:
        return 0


def ChoiceAdapter(enumtype):
    """To create choice filed in model from enum."""
    return (
        (item.value, item.name.replace("_", " ").title()) for item in enumtype
    )


def convert_excel_no_to_date(excel_date):
    """Function for convert excel in number format to date format."""
    try:
        dt = datetime.fromordinal(
            datetime(1970, 1, 1).toordinal() + int(excel_date) - 2
        )
    except Exception:
        dt = excel_date
    return dt


def convert_letter_to_number(value):
    """Return number corresponding to excel-style column."""
    number = -26
    for i in value:
        if i not in string.ascii_letters:
            return False
        number += ord(i.upper()) - 64 + 25
    return number


def create_alphabetic_list(limit):
    """Function for Generate alphabetic list in lexical order like column names
    in excel."""
    alpha_list = [
        string.ascii_uppercase[i]
        if i < 26
        else string.ascii_uppercase[i // 26 - 1]
             + string.ascii_uppercase[i % 26]
        for i in range(limit)
    ]
    return alpha_list


def filter_queryset(filter_class, data, queryset, request=None, node=None):
    """To run backend filtering manually."""
    if not node:
        filterset = filter_class(data=data, queryset=queryset, request=request)
    else:
        filterset = filter_class(
            data=data, queryset=queryset, request=request, node=node
        )
    if filterset is None:
        return queryset
    if not filterset.is_valid():
        raise Exception(filterset.errors)
    return filterset.qs


def camel_to_underscore(camel_case: str) -> str:
    """
    Convert a string in camelCase to snake_case.

    Parameters:
        camel_case (str): The input string in camelCase.

    Returns:
        str: The input string converted to snake_case.

    Examples:
        >>> camel_to_underscore("myVariableName")
        'my_variable_name'

        >>> camel_to_underscore("anotherExampleString")
        'another_example_string'
    """
    result = [camel_case[0].lower()]
    for char in camel_case[1:]:
        if char.isupper():
            result.append('_')
        result.append(char.lower())
    return ''.join(result)
