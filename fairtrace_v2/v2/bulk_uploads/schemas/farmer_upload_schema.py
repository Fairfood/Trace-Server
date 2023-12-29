from typing import Any
from typing import Dict
from typing import Optional

import pandas as pd
import pandera as pa
from pandera.typing import Series

from common.country_data import COUNTRY_WITH_PROVINCE
from v2.bulk_uploads.schemas.base import BaseUploadSchema
from v2.bulk_uploads.schemas.typing import (
    CountryDropDown, ConnectionTypeDropDown, ProvinceDropDown, Latitude,
    Longitude, Email, Phone)
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Node, SupplyChain


class FarmerUploadSchema(BaseUploadSchema):
    """Farmer upload schema model.

    This schema model represents the schema for uploading farmer data. It
    defines the structure and data types of the columns expected in the farmer
    data sheet.

    Attributes:
        first_name (Series[str]): The first name column in the data sheet. It
            is required and should contain string values.
        last_name (Series[str]): The last name column in the data sheet. It is
            required and should contain string values.
        connection_type (Series[str]): The connection type column in the data
            sheet. It is required and should contain string values.
        identification_no (Optional[Series[str]]): The identification number
            column in the data sheet. It is nullable and can contain string
            values.
        street_name (Optional[Series[str]]): The street name column in the data
            sheet. It is nullable and can contain string values.
        city (Series[str]): The city column in the data sheet. It is required
            and should contain string values.
        country (Series[str]): The country column in the data sheet. It is
            required and should contain string values.
        province (Series[str]): The province column in the data sheet. It is
            required and should contain string values.
        postal_code (Optional[Series[str]]): The postal code column in the data
            sheet. It is nullable and can contain string values.
        latitude (Optional[Series[float]]): The latitude column in the data
            sheet. It is nullable and can contain float values.
        longitude (Optional[Series[float]]): The longitude column in the data
            sheet. It is nullable and can contain float values.
        country_code (Optional[Series[str]]): The country code column in the
            data sheet. It is nullable and can contain string values.
        phone (Optional[Series[str]]): The phone column in the data sheet. It
            is nullable and can contain string values.
        email (Optional[Series[str]]): The email column in the data sheet. It
            is nullable and can contain string values.
        family_members (Optional[Series[float]]): The number of
            family members column in the data sheet. It is nullable and can
            contain float values.
        farm_area (Optional[Series[float]]): The farm area column in the data
            sheet. It is nullable and can contain float values.
        income_from_main_product (Optional[Series[float]]): The income from
            main product column in the data sheet. It is nullable and can
            contain float values.
        income_from_other_sources (Optional[Series[float]]): The income from
            other sources column in the data sheet. It is nullable and can
            contain float values.
    """
    first_name: Series[str] = pa.Field(coerce=True)
    last_name: Series[str] = pa.Field(coerce=True)
    connection_type: Series[ConnectionTypeDropDown] = pa.Field(nullable=True)
    identification_no: Optional[Series[str]] = pa.Field(
        nullable=True, coerce=True
    )
    street_name: Optional[Series[str]] = pa.Field(nullable=True)
    city: Optional[Series[str]] = pa.Field(nullable=True)
    country: Series[CountryDropDown]
    province: Series[ProvinceDropDown]
    postal_code: Optional[Series[str]] = pa.Field(nullable=True)
    latitude: Optional[Series[Latitude]] = pa.Field(nullable=True, coerce=True)
    longitude: Optional[Series[Longitude]] = pa.Field(
        nullable=True, coerce=True)
    country_code: Optional[Series[str]] = pa.Field(nullable=True, coerce=True)
    phone: Optional[Series[Phone]] = pa.Field(nullable=True, coerce=True)
    email: Optional[Series[Email]] = pa.Field(nullable=True, coerce=True)
    family_members: Optional[Series[pa.Float]] = pa.Field(
        nullable=True, coerce=True)
    farm_area: Optional[Series[pa.Float]] = pa.Field(nullable=True,
                                                     coerce=True)
    income_from_main_product: Optional[Series[pa.Float]] = pa.Field(
        nullable=True, coerce=True)
    income_from_other_sources: Optional[Series[pa.Float]] = pa.Field(
        nullable=True, coerce=True)

    @classmethod
    def run_presets(cls, context: Dict[str, Any]) -> None:
        node = context.get('node')
        suppy_chain = context.get('supply_chain')
        if node:
            cls.set_identification_no(node, suppy_chain)

    @classmethod
    def set_identification_no(cls,
                              node: Node,
                              supply_chain: SupplyChain):
        ids = node.get_supplier_chain(supply_chain=supply_chain)[0].filter(
            type=NODE_TYPE_FARM).values_list('identification_no', flat=True)
        if not cls.Config.metadata:
            cls.Config.metadata = {}
        cls.Config.metadata['ids'] = ids

    @pa.dataframe_check()
    def province_check(cls, df: pd.DataFrame) -> Series[bool]:
        """Check if the province is valid.

        This method checks if the province column in the data sheet contains
        valid province values.

        Args:
            df (pd.DataFrame): The data frame to check.

        Returns:
            Series[bool]: A series of boolean values indicating if the values
            in the province column are valid.
        """

        def validate_provinces(row):
            """Validation function."""
            country = row['country']
            province = row['province']

            if (country in COUNTRY_WITH_PROVINCE
                    and province in COUNTRY_WITH_PROVINCE[country]):
                return True
            else:
                return False

        return df.apply(validate_provinces, axis=1)

    @pa.check("identification_no",
              name="identification_no_check",
              error="Identification number already exists.",
              element_wise=True)
    def identification_no_check(cls, identification_no: str) -> bool:
        """ Check if the identification number is valid.

        This class method checks if the identification number is valid. The
        identification number is valid if it is not in the list of
        identification numbers.

        Args:
            identification_no (str): The identification number to check.

        Returns:
            bool: True if the identification number is valid, False otherwise.
        """

        ids = cls.get_schema_metadata().get('ids', [])
        return identification_no not in ids or identification_no == ""
