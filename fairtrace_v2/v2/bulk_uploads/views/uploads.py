import json
from typing import Tuple

import numpy as np
import pandas as pd
from common.drf_custom.mixins import inject_node
from common.drf_custom.views import IdencodeObjectViewSetMixin
from common.library import DateTimeEncoder, hash_dict, success_response, decode
from pandera.errors import SchemaErrors
from rest_framework import viewsets
from rest_framework.decorators import action
from v2.accounts import permissions as user_permissions
from v2.supply_chains import permissions as sc_permissions
from v2.supply_chains.models.profile import FarmerReference
from .. import tasks
from ..models.uploads import DataSheetUpload, DataSheetUploadSummary
from ..schemas.errors import SchemaFormattedErrors
from ..serializers.uploads import (DataSheetUploadSerializer,
                                   DataSheetUploadSummarySerializer)
from ..constants import TEMPLATE_TYPE_CONNECTION


class DataSheetUploadViewSet(
    IdencodeObjectViewSetMixin, viewsets.ModelViewSet
):
    """Data sheet upload ViewSet.

    This ViewSet handles operations related to data sheet uploads. It
    provides CRUD (Create, Read, Update, Delete) functionality for
    DataSheetUpload instances. Additionally, it supports a 'validate'
    action to validate the uploaded data sheet.
    """

    queryset = DataSheetUpload.objects.all()
    serializer_class = DataSheetUploadSerializer

    permission_classes = (
        user_permissions.IsAuthenticated,
        sc_permissions.HasNodeAccess,
    )

    def create(self, request, *args, **kwargs):
        """Create a new DataSheetUpload instance.

        This method creates a new DataSheetUpload instance and injects
        the current node as the source. It then delegates the handling
        of the request to the parent function.
        """

        inject_node(request, **kwargs)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Update an existing DataSheetUpload instance.

        This method updates an existing DataSheetUpload instance and
        injects the current node as the source. It then delegates the
        handling of the request to the parent function.
        """
        inject_node(request, **kwargs)
        return super().update(request, *args, **kwargs)

    @action(methods=["post"], detail=True, url_path="validate-row")
    def validate_row(self, request, *args, **kwargs):
        """
        Validate a specific row of the data sheet.

        This method is an action endpoint for validating a specific row of the
        data json associated with the detail record. It handles HTTP POST
        requests sent to the endpoint "validate-row".

        Returns:
        rest_framework.response.Response: The response object containing the
        validation result.
        """
        return self.validate(request, *args, **kwargs, upload_type="UPDATE")

    @action(methods=["post"], detail=True, url_path="validate")
    def validate(self, request, *args, **kwargs):
        """Validate the uploaded data sheet.

        This method validates the uploaded data sheet by performing schema
        validation. It retrieves the upload type and the DataSheetUpload
        instance, reads the JSON data from the request, and validates it using
        the schema.
        If validation succeeds, the data is updated in the instance. If
        validation fails, a ValidationError is raised.

        Args:
            request (Request): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The HTTP response containing the validation result.
        """
        upload_type = kwargs.get("upload_type")
        instance = self.get_object()

        if upload_type == "UPDATE":
            json_data = json.dumps(request.data)
            adapt_to_schema = False
        else:
            adapt_to_schema = True
            instance.data = {}
            instance.data_hash = {}
            json_data = json.dumps(instance.initial_data, cls=DateTimeEncoder)
        df = pd.read_json(json_data, orient="index")

        data, errors = self.validate_with_schema(
            df, instance, adapt_to_schema, upload_type)
        summary = self._create_or_update_summary(instance)

        return success_response(data={"data_count": len(instance.data),
                                      "errors_count": len(errors),
                                      "data": self._reformat(
                                          instance.data)[:10],
                                      "errors": self._reformat(errors)[:100],
                                      "summary": summary})

    @action(methods=["post"], detail=True, url_path="confirm")
    def confirm(self, request, *args, **kwargs):
        """
        Confirm the data sheet upload.

        This method is an action endpoint for confirming the data sheet upload.
        It handles HTTP POST requests sent to the endpoint "confirm".

        Parameters:
        request (rest_framework.request.Request): The HTTP request object.
        *args: Variable-length argument list.
        **kwargs: Arbitrary keyword arguments.

        Returns:
        rest_framework.response.Response: The response object containing the
        confirmation result.

        Raises:
        rest_framework.exceptions.ValidationError: If the data sheet upload is
        not confirmed and "force" parameter is not set to "true".
        """
        instance = self.get_object()
        force = request.data.get('force')
        instance.is_confirmed = True

        # If the data sheet upload is already confirmed and "force"
        # parameter is not set to "true", raise a duplication error.
        if not force == 'true':
            instance.save(check_type="is_confirmed")
        else:
            instance.save()
        tasks.bulk_upload.delay(instance.id)
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data)

    def validate_with_schema(self, df, instance,
                             adapt: bool, upload_type) -> Tuple[dict, dict]:
        """Validate the data sheet with the schema.

        This method validates the data sheet by comparing it against the
        schema. It retrieves the schema, extracts the relevant fields from the
        data sheet, renames the columns to match the schema fields, and
        performs schema validation. If validation succeeds, the data is updated
        in the instance. If validation fails, a ValidationError is raised.

        Args:
            df (DataFrame): The data sheet as a DataFrame.
            instance (DataSheetUpload): The DataSheetUpload instance to update.
            adapt (bool): Whether to adapt the data sheet to the schema.
        """
        schema = instance.template.schema
        schema.run_presets({"node": instance.node,
                            "supply_chain": instance.supply_chain})
        schema_fields = schema.__annotations__.keys()
        if adapt:
            field_position = instance.template.field_positions

            try:
                df = df[field_position.values()]
            except KeyError:
                return {}, {}
            df.columns = schema_fields

        df = schema.format_df(df)
        data, errors = self._validate_with_schema(df, schema)

        # Prepare the list of verified identification numbers if upload_type 
        # is "UPDATE"
        if upload_type == "UPDATE":
            identification_numbers = set()  # Using a set for O(1) lookups
            verified_data = instance.data
            
            # Collect all unique identification numbers from the verified data
            for verified in verified_data:
                if 'identification_no' in verified_data[verified]:
                    identification_numbers.add(
                        str(verified_data[verified]['identification_no']))

        # Create a helper function to handle adding errors
        def add_to_errors(index, row, error_message):
            if index not in errors:
                errors[index] = row
                errors[index].update({'errors': []})
            
            # Check if the error message's 'key' already exists in the errors list
            key_exists = False
            for error in errors[index]['errors']:
                if error.get('key') == error_message.get('key'):
                    # Update the reason if key exists
                    error['reason'] = error_message.get('reason')
                    key_exists = True
                    break
            
            # If the key does not exist, append the new error message
            if not key_exists:
                errors[index]['errors'].append(error_message)

        # Iterate through the DataFrame and check for duplicates and 
        # other conditions
        for index, row in df.iterrows():
            identification_no = row.get('identification_no')
            fair_id = row.get('fair_id', None)
            if pd.notna(identification_no):
                # Default to row_data being the current row if not popped 
                # from data
                row_data = row
                # Check for duplicates in the "UPDATE" case
                if upload_type == "UPDATE":
                    if str(identification_no) in identification_numbers:
                        # Remove the row from `data` and add it to `errors`
                        if index in data:
                            row_data = data.pop(index)
                        add_to_errors(index, row_data, {
                            'key': 'identification_no',
                            'reason': 'Duplicate Identification Number'
                        })
                else:
                    #Check for duplicates based on `identification_no` within 
                    # the DataFrame
                    duplicate_identification_numbers = df[
                        df.duplicated(
                            subset=['identification_no'], 
                            keep=False
                        )]
                    if index in duplicate_identification_numbers.index:
                        if index in data:
                            row_data = data.pop(index)
                        add_to_errors(index, row_data, {
                            'key': 'identification_no',
                            'reason': 'Duplicate Identification Number'
                        })
                
                # Check for existence of the identification number in 
                # FarmerReference model
                if instance.template.type == TEMPLATE_TYPE_CONNECTION:
                    node = self.kwargs.get("node", None)
                    suppliers = node.get_farmer_suppliers()
                    reference = FarmerReference.objects.filter(
                        number=identification_no, 
                        farmer__in=suppliers)
                    if fair_id:
                        reference = reference.exclude(farmer__id=decode(fair_id))
                    if reference.exists():
                        # Remove the row from `data` and add it to `errors`
                        if index in data:
                            row_data = data.pop(index)
                        add_to_errors(index, row_data, {
                            'key': 'identification_no',
                            'reason': 'Identification Number Already Exists'
                        })

        key_columns = ['first_name', 'last_name', 'country', 'province']
        if self.check_all_key_exist(list(schema_fields), key_columns):
            duplicates = self.find_duplicates(df, key_columns)
            errors.update(duplicates)
            data = {key: value for key, value in data.items() if key not in duplicates}

        if data:
            self.validate_hash(data, instance, errors)
            update_data = instance.data
            update_data.update(data)
            instance.data = update_data or {}
            instance.save()
        return data, errors

    def check_all_key_exist(self, df_keys=None, check_keys=None):
        if df_keys and check_keys:
            return all(item in df_keys for item in check_keys)
        return False

    @staticmethod
    def find_duplicates(df: pd.DataFrame, key_columns: list, fair_id_column: str = 'fair_id') -> dict:
        """
        Find duplicate rows in a DataFrame based on specified key columns,
        excluding rows with a specific fair_id after identifying duplicates.

        Args:
            df (DataFrame): The DataFrame to check for duplicates.
            key_columns (list): The list of column names to use as keys for finding duplicates.
            fair_id_column (str): The column name for the fair_id to be excluded from duplicates.

        Returns:
            dict: A dictionary where the keys are row indices and the values are dictionaries
                containing the details of duplicate rows and errors.
        """
        # Find duplicate rows based on the key columns
        duplicates = df[df.duplicated(subset=key_columns, keep="first")]

        # Prepare a dictionary to store duplicate information
        duplicate_info = {}

        # Collect duplicate rows and prepare the dictionary
        for index, row in duplicates.iterrows():
            if index not in duplicate_info:
                duplicate_info[index] = row.to_dict()

        # Create a new dictionary to store filtered results
        filtered_duplicates = {}

        # Filter out entries with a fair_id and copy the valid entries
        for index, row in duplicate_info.items():
            if pd.isna(row.get(fair_id_column)):
                filtered_duplicates[index] = row

        # Convert NaN and infinite values to None for JSON serialization
        for index, row in filtered_duplicates.items():
            for key, value in row.items():
                if isinstance(value, (float, np.float64)):
                    if pd.isna(value) or value == float('inf') or value == float('-inf'):
                        row[key] = None
                    else:
                        row[key] = float(value) 
                elif isinstance(value, pd.Timestamp):
                    row[key] = value.isoformat()  

        # Optionally, add an 'errors' field if needed (example: based on specific criteria)
        for index in filtered_duplicates.keys():
            filtered_duplicates[index]['errors'] = [{'key': "duplicate", 'reason': 'Duplicate Entry'}]  # Customize errors as needed

        return filtered_duplicates



    @staticmethod
    def _validate_with_schema(df, schema) -> Tuple[dict, dict]:
        """Validate the data sheet with the schema.

        This static method performs the actual validation of the data sheet
        against the schema. It uses the given DataFrame and schema to validate
        the data. If validation fails, a ValidationError is raised.

        Args:
            df (DataFrame): The data sheet as a DataFrame.
            schema (Schema): The schema to validate against.

        Returns:
            Tuple[dict, dict]: A tuple containing the valid data and any
            validation errors.
        """
        # Function to check if a string is JSON-loadable.
        def is_json_loadable(s):
            try:
                json.loads(s.replace("'", '"'))  # Replace single quotes with double quotes for JSON compatibility.
                return True
            except (ValueError, TypeError):
                return False

        def format_string(geo_data):
            if not pd.notnull(geo_data):
                return {}
            if isinstance(geo_data, str):
                if not geo_data.strip():
                    return {}
                if geo_data.startswith('"') or geo_data.endswith('"'):
                    geo_data = "'" + geo_data[1:-1] + "'"
                geo_data = geo_data.replace('(', '[')
                geo_data = geo_data.replace(')', ']')
                if geo_data.count("'") % 2 == 0:
                    geo_data = geo_data.replace("'", '"')
                if is_json_loadable(geo_data):
                    return json.loads(geo_data)
            return geo_data

        try:
            if 'geo_json' in df:
                df['geo_json'] = df['geo_json'].apply(lambda x: format_string(x))
            df.replace('', np.nan, inplace=True)
            df = schema.validate(df, lazy=True)
        except SchemaErrors as e:
            formatted_errors = SchemaFormattedErrors(e)
            return formatted_errors.data, formatted_errors.errors
        return df.fillna("").to_dict(orient="index"), {}

    @staticmethod
    def validate_hash(data, instance, errors):
        """Validate the hash values of the data sheet.

        This static method validates the hash values of the data sheet against
        the 'data_hash' values stored in the 'instance' of 'DataSheetUpload'.
        It checks for duplicates in the hash values and updates the 'data_hash'
        accordingly.
        If duplicates are found, the corresponding data entries are removed
        from the 'data' and 'errors' dictionaries, and duplicate error
        entries are added to the 'errors' dictionary.

        Args:
            data (dict): The data dictionary containing the data sheet entries.
            instance (DataSheetUpload): The DataSheetUpload instance.
            errors (dict): The dictionary containing the validation errors.
        """
        data_hash_map = dict(
            map(lambda item: (item[0], hash_dict(item[1])), data.items())
        )
        data_hash_list = instance.data_hash.values()

        duplicates = set(data_hash_list).intersection(data_hash_map.values())

        if duplicates:
            duplicate_indices = [
                k for k, v in data_hash_map.items() if v in duplicates
            ]
            for index in duplicate_indices:
                data_hash_map.pop(index)
                error = data.pop(index)
                error["errors"] = [{
                    "key": "duplicate",
                    "reason": "Duplicate entry",
                }]
                errors[index] = error
        update_hash_data = instance.data_hash
        update_hash_data.update(data_hash_map)
        instance.data_hash = update_hash_data or {}

    @staticmethod
    def _reformat(data):
        """
        Reformat the data dictionary.

        This method takes a dictionary where the keys are row indices and the
        values are dictionaries containing row data. It updates each row
        dictionary by adding an "index" key with the corresponding row index as
        its value. The method then returns a list of the modified row
        dictionaries.

        Parameters:
        data (dict): A dictionary where keys are integers representing row
            indices, and values are dictionaries containing row data.

        Returns:
        list: A list of dictionaries containing row data, each with an
            additional "index" key.
        """
        list(map(lambda row: row[1].update({"index": row[0]}), data.items()))
        return list(data.values())

    @staticmethod
    def _create_or_update_summary(instance):
        """
        Create or update a DataSheetUploadSummary object based on the input
        data.

        Parameters:
            instance (DataSheetUpload): The instance to associate with the
                                         summary object.
        """

        json_data = json.dumps(instance.data, cls=DateTimeEncoder)

        df = pd.read_json(json_data, orient="index")
        df.replace('', np.nan, inplace=True)
        column_names = df.columns

        farmers_to_update = (df["fair_id"].count()
                             if "fair_id" in column_names
                             else 0)

        farmers_to_add = df.shape[0] - farmers_to_update
        total_price = (df["price"].sum()
                       if "price" in column_names
                       else 0)
        transactions_to_add = 0
        total_quantity = 0
        average_quantity = 0
        highest_quantity = 0
        lowest_quantity = 0

        if "quantity" in column_names:
            transactions_to_add = df.shape[0]
            total_quantity = df["quantity"].sum()
            average_quantity = df["quantity"].mean()
            highest_quantity = df["quantity"].max()
            lowest_quantity = df["quantity"].min()

        obj, _ = DataSheetUploadSummary.objects.get_or_create(upload=instance)
        obj.farmers_to_add = farmers_to_add
        obj.farmers_to_update = farmers_to_update
        obj.transactions_to_add = transactions_to_add
        obj.total_price = total_price
        obj.total_quantity = total_quantity
        obj.average_quantity = average_quantity
        obj.highest_quantity = highest_quantity
        obj.lowest_quantity = lowest_quantity
        obj.save()
        serializer = DataSheetUploadSummarySerializer(obj)
        return serializer.data
