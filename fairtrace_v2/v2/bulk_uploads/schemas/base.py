import copy
import inspect
from typing import Any
from typing import Dict
from typing import get_args

import pandera as pa
from pandera.api.pandas import model
from pydantic.typing import NoneType


class BaseUploadSchema(pa.DataFrameModel):
    """Base class for all upload schemas."""

    @classmethod
    def run_presets(cls, context: Dict[str, Any]) -> None:
        pass

    @classmethod
    def get_schema_metadata(cls):
        """Get the metadata of the schema class.

        This class method retrieves the metadata of the schema class.
        """
        try:
            return cls.get_metadata().get(cls.__name__).get('dataframe')
        except AttributeError:
            return {}
        except KeyError:
            return {}

    @classmethod
    def get_fields(cls) -> Dict[str, Any]:
        """Get the fields of the class.

        This class method retrieves the field definitions from the
        '__annotations__' attribute of the class, which contains the type hints
         for the fields.

        Returns:
            Dict[str, Any]: A dictionary of field names mapped to their
            corresponding types.
        """
        remove_cls = (BaseUploadSchema, pa.DataFrameModel, model.BaseModel,
                      object)
        fields = {}
        for klass in cls.__mro__[::-1]:
            if klass not in remove_cls:
                fields.update(klass.__annotations__)
        return fields

    @classmethod
    def get_dict_fields(cls) -> Dict[str, Any]:
        """Get the fields of the class.

        This class method retrieves the field definitions from the
        '__dict__' attribute of the class, which contains the type hints
         for the fields.

        Returns:
            Dict[str, Any]: A dictionary of field names mapped to their
            corresponding types.
        """
        remove_cls = (pa.DataFrameModel, model.BaseModel, object)
        fields = {}
        for klass in cls.__mro__[::-1]:
            if klass not in remove_cls:
                fields.update(klass.__dict__)
        return fields

    @classmethod
    def get_optional_fields(cls) -> Dict[str, Any]:
        """Get the optional fields of the class.

        This class method retrieves the field definitions from the 'get_fields'
        method and checks if the field type contains 'NoneType' in its type
        hints using the 'get_args' function from the 'typing' module.

        Returns:
            Dict[str, Any]: A dictionary of optional field names mapped to
            their corresponding types.
        """
        optional_fields = {}
        for field, value in cls.get_fields().items():
            args = get_args(value)
            if NoneType in args:
                optional_fields[field] = value
        return optional_fields

    @classmethod
    def get_mandatory_fields(cls) -> Dict[str, Any]:
        """Get the mandatory fields of the class.

        This class method retrieves all field definitions from the 'get_fields'
        method and removes the optional fields obtained from the
        'get_optional_fields' method.

        Returns:
            Dict[str, Any]: A dictionary of mandatory field names mapped to
            their corresponding types.
        """
        fields = cls.get_fields().copy()
        for field, _ in cls.get_optional_fields().items():
            fields.pop(field)
        return fields

    @classmethod
    def create_modified_schema(cls, only_fields):
        """Create a modified schema class with specified fields.

        This class method creates a modified schema class based on the
        specified 'only_fields'. It retrieves the field definitions and
        annotations for the specified fields from the class and creates a new
        schema class with the modified fields.

        Args:
            only_fields (Iterable[str]): The fields to include in the modified
            schema class.

        Returns:
            type: The modified schema class.
        """
        fields = {}
        ann = {}
        for field in only_fields:
            try:
                fields[field] = copy.deepcopy(cls.get_dict_fields()[field])
                ann[field] = cls.get_fields()[field]
            except KeyError:
                continue

        class_methods = inspect.getmembers(cls, inspect.ismethod)
        fields.update(dict(class_methods))

        # Create a new schema class with the modified fields
        modified_schema = type(
            f"Modified{cls.__name__}", (pa.DataFrameModel,), fields
        )
        setattr(modified_schema, "__annotations__", ann)
        return modified_schema
