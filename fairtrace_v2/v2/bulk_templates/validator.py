"""Add custom types into the cerberus validator."""
from datetime import datetime

import cerberus
from cerberus import Validator
from v2.bulk_templates.custom_types import Currency
from v2.bulk_templates.custom_types import FarmerId
from v2.bulk_templates.custom_types import TraceId
from v2.bulk_templates.custom_types import Unit


class ExcelValidator(Validator):
    """Validates Excel."""

    types_mapping = Validator.types_mapping.copy()
    types_mapping["farmerid"] = cerberus.TypeDefinition(
        "farmerid", (FarmerId,), ()
    )
    types_mapping["traceid"] = cerberus.TypeDefinition(
        "traceid", (TraceId,), ()
    )
    types_mapping["currency"] = cerberus.TypeDefinition(
        "currency", (Currency,), ()
    )
    types_mapping["unit"] = cerberus.TypeDefinition("unit", (Unit,), ())


def to_date(s):
    """Convert to datetime."""
    return datetime.strptime(s, "%Y-%m-%d")
