"""Country data The json file country_data.json has a json list of countries,
their latlong, dialcode, 2 digit alphabetical code and subdivision of all the
countries.

Format
[

    "<country_name:str>": {
        "latlong": [
            <latitude:float>,
            <longitude:float>
        ],
        "dial_code": "<phonenumber_dialcode_without+:str>",
        "alpha_2": "<2digit_code>",
        "sub_divisions": [
            <list_of_subdivisions:list(str)>
        ]
    },
]

This file converts the json file to python data dict.
"""
import json
import os

from django.conf import settings

country_file_path = os.path.join(
    settings.BASE_DIR,
    "common",
    "country_data",
    "country_data_with_province_latlong.json",
)

with open(country_file_path) as country_file:
    COUNTRIES = json.loads(country_file.read())
    COUNTRY_LIST = list(COUNTRIES.keys())
    COUNTRY_WITH_PROVINCE = {
        i: list(v["sub_divisions"].keys()) for i, v in COUNTRIES.items()
    }
    DIAL_CODES = ["+" + i["dial_code"] for i in COUNTRIES.values()]

    DIAL_CODE_NAME_MAP = {
        "+" + val["dial_code"]: "%s (+%s)" % (k, val["dial_code"])
        for k, val in COUNTRIES.items()
    }
    # DIAL_CODES_WITH_NAME = ['%s (+%s)' % (k, val['dial_code']) for k,
    # val in COUNTRIES.items()]
    DIAL_CODES_WITH_NAME = list(DIAL_CODE_NAME_MAP.values())
