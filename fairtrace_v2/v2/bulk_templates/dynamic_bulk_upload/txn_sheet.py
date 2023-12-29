import operator
from datetime import datetime

import numpy as np
import pandas as pd
from common import library as comm_lib
from common.exceptions import BadRequest
from common.library import _decode
from django.db.utils import ProgrammingError
from v2.bulk_templates import constants as temp_constants
from v2.bulk_templates.choices import FieldType
from v2.products import constants as prod_constants
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Operation
from v2.transactions.models import ExternalTransaction

try:
    FARM_OPERATION_CHOICES = [
        o.name for o in Operation.objects.filter(node_type=NODE_TYPE_FARM)
    ]
except ProgrammingError:
    FARM_OPERATION_CHOICES = []


class DynamicExcelProcessor:
    """Class for get farmer with their txn data from excel sheet.

    excel_obj   : Object of bulk file model.
    row_data    : Array save excel data.
    """

    excel_obj = None
    row_data: list = []
    product = None

    def __init__(self, excel_obj):
        """To perform function __init__."""
        self.excel_obj = excel_obj
        self._read_excel()
        try:
            template = self.excel_obj.template
        except Exception:
            template = self.excel_obj
        if not template.is_title_set():
            self._set_title()

    def _find_col_head(self):
        """Function for find first row from file and replace column value
        unnamed to None."""
        row_head = []
        for value in self.df.columns.values:
            if value.startswith("Unnamed:"):
                value = value.replace("Unnamed: ", "None ")
                value = value[: value.rindex(" ")] + ""
            row_head.append(value)
        return row_head

    def _read_excel(self):
        """Read excel and covert to 2D array, save to row_data."""
        try:
            self.df = pd.read_excel(
                self.excel_obj.save_temp_excel(), dtype="object"
            )
        except Exception as e:
            raise e
        self.df = self.df.fillna("None")
        col_head = self._find_col_head()
        self.row_data = self.df.to_numpy()
        # set 2D array with col heading.
        self.row_data = np.insert(self.row_data, 0, col_head, axis=0)
        # find total column count in Excel and create an alphabetic
        # list and set it as column heading in 2D array
        excel_col = comm_lib.create_alphabetic_list(self.df.shape[1])
        self.row_data = np.insert(self.row_data, 0, excel_col, axis=0)
        return True

    def _convert_datetime_to_date(self, preview_data):
        """To convert nd array datetime column to date format."""
        pre_idx = 0
        for row in preview_data:
            row_inx = 0
            for data in row:
                if (
                    type(preview_data[pre_idx][row_inx])
                    == pd._libs.tslibs.timestamps.Timestamp
                ):
                    preview_data[pre_idx][row_inx] = datetime.strftime(
                        preview_data[pre_idx][row_inx].to_pydatetime(),
                        "%d-%m-%Y",
                    )
                elif type(preview_data[pre_idx][row_inx]) == datetime:
                    preview_data[pre_idx][row_inx] = datetime.strftime(
                        preview_data[pre_idx][row_inx], "%d-%m-%Y"
                    )
                row_inx = row_inx + 1
            pre_idx = pre_idx + 1
        return True

    def get_preview(self, row_count=temp_constants.PREVIEW_ROW_COUNT):
        """To perform function get_preview."""
        # get 2D array for preview the data from excel.
        preview_data = self.row_data[:row_count]
        self._convert_datetime_to_date(preview_data)
        return preview_data

    def _set_title(self):
        """Function for find title of the excel row and save to template
        object."""
        # r_sum = {}
        # for i in range(len(self.df.index)):
        #     r_sum.update({i: self.df.iloc[i].isnull().sum()})
        # title_row = min(r_sum, key=r_sum.get)
        row_count = []
        for index, row in self.df.iterrows():
            row_count.append(self.df.iloc[index].isnull().sum())
        try:
            index, value = min(
                enumerate(row_count), key=operator.itemgetter(1)
            )
        except Exception:
            raise BadRequest(
                "The submitted excel is empty. Please verify file."
            )
        self.excel_obj.title_row = index
        self.excel_obj.data_row = index + 1
        self.excel_obj.save()
        return True

    def last_row(self):
        """Function for find last row from excel file and return last row index
        value."""
        last = self.df.tail(1)
        try:
            last_row = last.index.values[0]
        except IndexError:
            raise BadRequest(
                "The submitted excel is empty. " "Please verify file."
            )
        return last_row

    def set_field_value(self, fields):
        """Function for set unit value."""
        for field in fields:
            for key, value in prod_constants.UNIT_CHOICES:
                if value == field["value"]:
                    field["value"] = key
        return True

    def duplicate_checker(self, fields):
        """function for set field values for duplicate checking."""
        type_fields = {}
        for field in fields:
            if field["type"] == FieldType.FARMER_ID.value:
                field["value"] = comm_lib._decode(field["value"])
            type_fields[field["key"]] = field["value"]
        return type_fields

    def get_meta(self, type_fields, supply_chain):
        """if field type is farmer id or identification id then pass farmer id
        details as meta data."""
        meta = {}
        if type_fields["type"] == FieldType.FARMER_ID.value:
            if type_fields["valid"]:
                farmer = Farmer.objects.get(id=_decode(type_fields["value"]))
                meta["name"] = farmer.full_name
                meta["id"] = farmer.idencode
        if type_fields["type"] == FieldType.TRACE_ID.value:
            if type_fields["valid"]:
                farmer = Farmer.objects.filter(
                    identification_no=type_fields["value"],
                    managers=self.excel_obj.node.id,
                    nodesupplychain__supply_chain=supply_chain.id,
                ).first()
                meta["identification_no"] = type_fields["value"]
                if farmer:
                    meta["name"] = farmer.full_name
                    meta["id"] = farmer.idencode
        return meta

    # def encode_id_field(self, fields):
    #     """
    #     Function for encode farmer id field.
    #     """
    #     for field in fields:
    #         if field['type'] == FieldType.FARMER_ID.value:
    #             field['value'] = comm_lib._encode(field['value'])
    #     return True
    def _validate_farmer_id_no(self, validated_fields, prev_value, sc):
        """Function for validate farmer identification number by company and
        supply chain."""
        issue_count = 1
        if validated_fields["valid"]:
            issue_count = 0
            farmers = Farmer.objects.filter(
                identification_no=prev_value,
                managers=self.excel_obj.node.id,
                nodesupplychain__supply_chain=sc.id,
            ).exists()
            if not farmers:
                issue_count = 1
                validated_fields["valid"] = False
                message = (
                    f'{{{validated_fields["label"]}:[Farmer not connected to'
                    " this company/supply chain]}"
                )
                validated_fields["message"] = message
        return issue_count

    def validate_row(self, row, product, sc):
        """function for validate row from excel and set issue count, metadata.

        also check row data is duplicate or not.
        """
        row_data = {
            "is_select": False,
            "is_removed": False,
            "is_keep": False,
            "is_duplicate": False,
            "duplicate": {"id": None},
            "issue_count": 0,
            "valid": True,
            "fields": [],
        }
        temp_fields = self.excel_obj.template.template_fields.all()
        for temp_field in temp_fields:
            try:
                fields, issue_count = temp_field.validate_data(
                    row[temp_field.column_pos]
                )
            except Exception:
                raise BadRequest("Incorrect linking of template fields")
            if fields["type"] == FieldType.TRACE_ID.value:
                issue_count = self._validate_farmer_id_no(
                    fields, row[temp_field.column_pos], sc
                )
            row_data["fields"].append(fields)
            row_data["issue_count"] += issue_count
            row_data["valid"] &= fields["valid"]
            fields["meta"].update(self.get_meta(fields, sc))
            self.set_field_value(row_data["fields"])
        # transaction duplicate is only check when row data is valid.
        if row_data["issue_count"] == 0:
            txn_row = self.duplicate_checker(row_data["fields"])
            (
                row_data["is_duplicate"],
                row_data["duplicate"]["id"],
            ) = self.check_duplicate_txn(txn_row, product)
            if row_data["is_duplicate"]:
                row_data["valid"] = False
            # self.encode_id_field(row_data['fields'])
        return row_data

    def validate_txn_file(self, product, sc):
        """Read excel data from 2D array in range between data_row to last_row,
        and return validated response."""
        excel_data = []
        data_row = self.excel_obj.template.data_row
        last_row = self.last_row() + 3
        for row in self.row_data[data_row:last_row]:
            if not np.all(row == "None"):
                row_data = self.validate_row(row, product, sc)
                excel_data.append(row_data)
        return excel_data

    def validate(self, product=None, supply_chain=None):
        """To validate farmer bulk transaction excel rows."""
        data_list = self.validate_txn_file(product, supply_chain)
        response = {}
        global_validity = True
        for data in data_list:
            global_validity &= data["valid"]
        # check double entry
        self.check_double_entry(data_list)
        for data in data_list:
            global_validity &= data["valid"]

        response["count"] = len(data_list)
        response["valid"] = global_validity
        response["message"] = ""
        response["product"] = {"id": product.idencode, "name": product.name}
        response["row_data"] = data_list
        return response

    def check_duplicate_txn(self, txn, product):
        """Function to check transaction is already exists or not.

        Request Params:
            txn(dict)   :transaction data
        Response:
            is_duplicate(bool)          :true or false value.
            duplicate_txn_id(idencode)  :duplicate txn id.
        """
        txn["result_batches__product__name"] = product.name
        txn["result_batches__product__id"] = product.id
        txn["destination__id"] = self.excel_obj.node.id
        # Quantity field is defined as decimal in model. Then quantity
        # filtering is not work properly when it has more digits after decimal.
        # so to get exact quantity convert the value type from float to str.
        txn["result_batches__current_quantity"] = (
            str(txn["result_batches__current_quantity"])
            if (txn.get("result_batches__current_quantity", None))
            else None
        )
        external_trans = ExternalTransaction.objects.filter(**txn)
        if external_trans:
            return True, external_trans[0].idencode
        return False, None

    def check_double_entry(self, txn):
        """Function for check double entry of transaction details in excel."""
        seen_list = []
        for txn_row in txn:
            txn_row["double_entry"] = {"double_entry": False, "index": ""}
            if not txn_row["valid"]:
                continue
            if txn_row["fields"] in seen_list:
                index_val = seen_list.index(txn_row["fields"])
                txn_row["double_entry"] = {
                    "double_entry": True,
                    "index": index_val,
                }
                txn_row["valid"] = False
            seen_list.append(txn_row["fields"])
        return True
