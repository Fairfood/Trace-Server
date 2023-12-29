#!/usr/bin/env python
# coding=utf-8
"""Constants of the app bulk_templates."""
from v2.bulk_templates import custom_types
from v2.bulk_templates.choices import FieldType
from v2.bulk_templates.custom_types import FarmerId
from v2.bulk_templates.custom_types import TraceId

NODE_TEMPLATE_STATUS_ACTIVE = 1
NODE_TEMPLATE_STATUS_INACTIVE = 2

NODE_TEMPLATE_STATUS_CHOICES = (
    (NODE_TEMPLATE_STATUS_ACTIVE, "Active"),
    (NODE_TEMPLATE_STATUS_INACTIVE, "Inactive"),
)

TEMPLATE_TYPE_TXN = 1
TEMPLATE_TYPE_CONNECTION = 2

TEMPLATE_TYPE_CHOICES = (
    (TEMPLATE_TYPE_TXN, "Transaction"),
    (TEMPLATE_TYPE_CONNECTION, "Connection"),
)

TEMPLATE_VISIBILITY_PUBLIC = 1
TEMPLATE_VISIBILITY_PRIVATE = 2
TEMPLATE_VISIBILITY_HIDDEN = 3

TEMPLATE_VISIBILITY_CHOICES = (
    (TEMPLATE_VISIBILITY_PUBLIC, "Public"),
    (TEMPLATE_VISIBILITY_PRIVATE, "Private"),
    (TEMPLATE_VISIBILITY_HIDDEN, "Hidden"),
)

SCHEMAS = {
    FieldType.FARMER_ID: {"type": "farmerid", "coerce": FarmerId},
    FieldType.LATITUDE: {"type": "float", "min": -180.00, "max": 180.00},
    FieldType.STRING: {"type": "string"},
    FieldType.INTEGER: {"type": "integer"},
    FieldType.FLOAT: {"type": "float"},
    FieldType.DATE: {"type": "date"},
    FieldType.PHONE: {"type": "integer"},
    FieldType.EMAIL: {
        "type": "string",
        "regex": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    },
    FieldType.TRACE_ID: {"type": "traceid", "coerce": TraceId},
    FieldType.CURRENCY: {"type": "currency", "coerce": custom_types.Currency},
    FieldType.UNIT: {"type": "unit", "coerce": custom_types.Unit},
}

PREVIEW_ROW_COUNT = 20
TEMP_FILE = "test.xlsx"

FIELD_SPAN_HALF = 1
FIELD_SPAN_FULL = 2

FIELD_SPAN_CHOICES = (
    (FIELD_SPAN_HALF, "Half span"),
    (FIELD_SPAN_FULL, "Full span"),
)

CUSTOM_TEMP_NAME = "Bulk upload template"
