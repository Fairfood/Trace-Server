import re
from abc import ABC
from typing import Iterable, Optional, Union

import pandas as pd
from common.country_data import COUNTRIES
from pandera import dtypes
from pandera.engines import pandas_engine


@pandas_engine.Engine.register_dtype
@dtypes.immutable
class CountryDropDown(pandas_engine.NpString, ABC):
    def check(
            self,
            pandera_dtype: dtypes.DataType,
            data_container: Optional[pd.Series] = None,
    ) -> Union[bool, Iterable[bool]]:
        # ensure that the data container's data type is a string,
        # using the parent class's check implementation
        correct_type = super().check(pandera_dtype)
        if not correct_type:
            return correct_type

        # ensure the filepaths actually exist locally
        return data_container.map(lambda x: x in COUNTRIES.keys())

    def __str__(self) -> str:
        return str(self.__class__.__name__)

    def __repr__(self) -> str:
        return f"DataType({self})"


@pandas_engine.Engine.register_dtype
@dtypes.immutable
class ConnectionTypeDropDown(pandas_engine.NpString, ABC):
    pass


@pandas_engine.Engine.register_dtype
@dtypes.immutable
class ProvinceDropDown(pandas_engine.NpString, ABC):
    pass


@pandas_engine.Engine.register_dtype
@dtypes.immutable
class Latitude(pandas_engine.NpString, ABC):
    def check(
            self,
            pandera_dtype: dtypes.DataType,
            data_container: Optional[pd.Series] = None,
    ) -> Union[bool, Iterable[bool]]:
        # ensure that the data container's data type is numeric,
        # using the parent class's check implementation
        correct_type = super().check(pandera_dtype)
        if not correct_type:
            return correct_type
        
        data_container = data_container.astype(str)

        # validate latitude and longitude format
        exp = re.compile(r"-?\d+\.\d+")
        format_valid = (
            data_container.str.match(exp) | 
            data_container.eq("nan")
            )

        # validate latitude range (-90 to 90) and longitude range (-180 to 180)
        float_data = pd.to_numeric(data_container, errors="coerce")
        lat_range_valid = (
            float_data.isna() | 
            ((float_data >= -90) & (float_data <= 90))
            )

        return format_valid & lat_range_valid

    def __str__(self) -> str:
        return str(self.__class__.__name__)

    def __repr__(self) -> str:
        return f"DataType({self})"


@pandas_engine.Engine.register_dtype
@dtypes.immutable
class Longitude(pandas_engine.NpString, ABC):
    def check(
            self,
            pandera_dtype: dtypes.DataType,
            data_container: Optional[pd.Series] = None,
    ) -> Union[bool, Iterable[bool]]:
        # ensure that the data container's data type is numeric,
        # using the parent class's check implementation
        correct_type = super().check(pandera_dtype)
        if not correct_type:
            return correct_type
        
        data_container = data_container.astype(str)


        # validate latitude and longitude format
        exp = re.compile(r"-?\d+\.\d+")
        format_valid = (
            data_container.str.match(exp) | 
            data_container.eq("nan")
            )

        # validate latitude range (-90 to 90) and longitude range (-180 to 180)
        float_data = pd.to_numeric(data_container, errors="coerce")
        long_range_valid = (
            float_data.isna() | 
            ((float_data >= -180) & (float_data <= 180))
            )

        return format_valid & long_range_valid

    def __str__(self) -> str:
        return str(self.__class__.__name__)

    def __repr__(self) -> str:
        return f"DataType({self})"


@pandas_engine.Engine.register_dtype
@dtypes.immutable
class Email(pandas_engine.NpString, ABC):
    def check(
            self,
            pandera_dtype: dtypes.DataType,
            data_container: Optional[pd.Series] = None,
    ) -> Union[bool, Iterable[bool]]:
        # Ensure that the data container's data type is a string,
        # using the parent class's check implementation
        correct_type = super().check(pandera_dtype)
        if not correct_type:
            return correct_type

        # Validate email format
        exp = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        return data_container.str.match(exp)

    def __str__(self) -> str:
        return str(self.__class__.__name__)

    def __repr__(self) -> str:
        return f"DataType({self})"


@pandas_engine.Engine.register_dtype
@dtypes.immutable
class Phone(pandas_engine.NpString, ABC):
    def check(
            self,
            pandera_dtype: dtypes.DataType,
            data_container: Optional[pd.Series] = None,
    ) -> Union[bool, Iterable[bool]]:
        # Ensure that the data container's data type is a string,
        # using the parent class's check implementation
        correct_type = super().check(pandera_dtype)
        if not correct_type:
            return correct_type

        # Validate phone number format without country code
        # Only allows digits and optional hyphens or spaces between digits
        exp = re.compile(r"\d+(-|\s)?\d+")
        return data_container.str.match(exp)

    def __str__(self) -> str:
        return str(self.__class__.__name__)

    def __repr__(self) -> str:
        return f"DataType({self})"


@pandas_engine.Engine.register_dtype
@dtypes.immutable
class LocationTypeDropDown(pandas_engine.NpString, ABC):
    pass