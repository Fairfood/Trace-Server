import re

from common import library as comm_lib
from common.country_data import COUNTRY_LIST
from common.country_data import COUNTRY_WITH_PROVINCE
from common.country_data import DIAL_CODES_WITH_NAME
from common.excel_templates import cells
from common.excel_templates.constants import VALUE_CHANGED
from common.excel_templates.constants import VALUE_NEW
from common.excel_templates.constants import VALUE_UNCHANGED
from common.excel_templates.excel import Excel
from common.excel_templates.excel import ExcelRow
from django.db.utils import ProgrammingError
from v2.products import constants as prod_constants
from v2.products.models import Product
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Operation
from v2.transactions.choices import FieldType
from v2.transactions.constants import DUPLICATE_EX_TXN
from v2.transactions.constants import DUPLICATE_FARMER
from v2.transactions.models import ExternalTransaction

try:
    FARM_OPERATION_CHOICES = [
        o.name for o in Operation.objects.filter(node_type=NODE_TYPE_FARM)
    ]
except ProgrammingError:
    FARM_OPERATION_CHOICES = []


class PrimaryOperationCell(cells.ChoiceCell):
    """Class to handle PrimaryOperationCell and functions."""

    def validate(self):
        """To perform function validate."""
        check = super(PrimaryOperationCell, self).validate()
        if not check["valid"]:
            return check
        if self.value:
            try:
                check["value"] = Operation.objects.get(
                    name=self.value, node_type=NODE_TYPE_FARM
                ).idencode
            except Exception:
                check["valid"] = False
                check["value"] = self.to_representation
                check["message"] += "%s is not a valid choice." % self.value
                check = self.check_issue(self.heading, check)
        return check

    @property
    def to_representation(self):
        """To perform function to_representation."""
        return self.value


class UnitCell(cells.CharCell):
    """Class to handle UnitCell and functions."""

    def validate(self):
        """To perform function validate."""
        check = super(UnitCell, self).validate()
        check["type"] = FieldType.CHOICE.value
        return check

    @property
    def to_representation(self):
        """To perform function to_representation."""
        if self.value:
            for key, value in prod_constants.UNIT_CHOICES:
                if value == self.value:
                    return key
            else:
                return self.value
        else:
            return self.value


class FarmerWithTransactionExcelRow(ExcelRow):
    """Class for get farmer data from each row in excel sheet."""

    id = cells.CharCell(
        heading="FairID",
        column="B",
        write=True,
        required=False,
        source="idencode",
    )
    first_name = cells.CharCell(heading="First Name", column="C", write=True)
    last_name = cells.CharCell(heading="Last Name", column="D", write=True)
    primary_operation = PrimaryOperationCell(
        heading="Connection Type",
        column="E",
        choices=FARM_OPERATION_CHOICES,
        write=True,
        source="primary_operation_name",
    )
    identification_no = cells.CharCell(
        heading="Identification number", column="F", required=False, write=True
    )

    street = cells.CharCell(
        heading="Street + Number", column="G", required=False, write=True
    )
    city = cells.CharCell(heading="City or Village", column="H", write=True)
    country = cells.CountryCell(
        heading="Country", column="I", choices=COUNTRY_LIST, write=True
    )
    province = cells.DependantChoiceCell(
        heading="Province or State",
        column="J",
        choices=COUNTRY_WITH_PROVINCE,
        selection="country",
        write=True,
    )
    zipcode = cells.CharCell(
        heading="Postal code", column="K", required=False, write=True
    )

    latitude = cells.FloatCell(
        heading="Latitude", column="L", required=False, write=True
    )
    longitude = cells.FloatCell(
        heading="Longitude", column="M", required=False, write=True
    )

    dial_code = cells.DialCodeCell(
        heading="Country Code",
        column="N",
        choices=DIAL_CODES_WITH_NAME,
        required=False,
        write=True,
        source="dial_code_text",
    )
    phone = cells.PhoneCell(
        heading="Phone Number",
        column="O",
        required=False,
        write=True,
        source="phone_number",
    )
    email = cells.EmailCell(
        heading="Email", column="P", required=False, write=True
    )

    family_members = cells.IntegerCell(
        heading="Number of members in family",
        column="Q",
        required=False,
        hidden=True,
        write=True,
    )
    farm_area = cells.CharCell(
        heading="Farm area",
        column="R",
        required=False,
        hidden=True,
        write=True,
    )
    income_from_main_product = cells.FloatCell(
        heading="Income from main product",
        column="S",
        required=False,
        hidden=True,
        write=True,
    )
    income_from_other_sources = cells.CharCell(
        heading="Income from other sources",
        column="T",
        required=False,
        hidden=True,
        write=True,
    )

    product_id = cells.CharCell(
        heading="Product ID", column="U", hidden=True, write=True, update=False
    )
    product = cells.CharCell(
        heading="Product", column="V", write=True, update=False
    )
    transaction_date = cells.DateCell(
        heading="Transaction Date", column="W", update=False
    )
    unit = UnitCell(heading="Unit", column="X", update=False)
    currency = cells.CurrencyCell(heading="Currency", column="Y", update=False)
    price_per_unit = cells.FloatCell(
        heading="Price per unit", column="Z", update=False
    )
    quantity = cells.FloatCell(
        heading="Total quantity", column="AA", update=False
    )
    invoice_number = cells.CharCell(
        heading="Invoice #", column="AB", required=False, update=False
    )

    class Meta:
        name = "farmers"
        fields = [
            "id",
            "first_name",
            "last_name",
            "primary_operation",
            "identification_no",
            "street",
            "city",
            "country",
            "province",
            "zipcode",
            "latitude",
            "longitude",
            "dial_code",
            "phone",
            "email",
            "family_members",
            "farm_area",
            "income_from_main_product",
            "income_from_other_sources",
            "product_id",
            "product",
            "transaction_date",
            "unit",
            "currency",
            "price_per_unit",
            "quantity",
            "invoice_number",
        ]

        related_model = Farmer
        id_field = "id"


class FarmerWithTransactionExcel(Excel):
    """Class for get farmer data from excel sheet."""

    class Meta:
        first_row = 8
        row_class = FarmerWithTransactionExcelRow
        backend_sheet = "Data"
        data_sheet = "Datasheet"
        fields: list = []
        mandatory_column = "C"
        farmer_fields = [
            "id",
            "first_name",
            "last_name",
            "primary_operation",
            "identification_no",
            "street",
            "city",
            "country",
            "province",
            "zipcode",
            "latitude",
            "longitude",
            "dial_code",
            "phone",
            "email",
            "family_members",
            "farm_area",
            "income_from_main_product",
            "income_from_other_sources",
        ]
        transaction_fields = [
            "product_id",
            "product",
            "transaction_date",
            "unit",
            "currency",
            "price_per_unit",
            "quantity",
            "invoice_number",
        ]

    def _validate_identification_no(self, farmer_transaction, node, sc):
        """To perform function _validate_identification_no."""
        id_no_data = farmer_transaction["identification_no"]
        try:
            if Farmer.objects.filter(
                identification_no=id_no_data["value"],
                managers=node,
                nodesupplychain__supply_chain=sc,
            ).exists():
                id_no_data["valid"] = False
                id_no_data["message"] += (
                    "%s already exists" % id_no_data["value"]
                )
                cell_obj = cells.Cell(
                    heading="Identification number", column="E"
                )
                farmer_transaction["identification_no"] = cell_obj.check_issue(
                    "identification_no", id_no_data
                )
        except Exception:
            pass
        return True

    def _validate_fair_id(self, farmer_transaction, node):
        """To perform function _validate_fair_id."""
        fair_id = farmer_transaction["id"]
        try:
            farmer_object = Farmer.objects.get(
                id=comm_lib._decode(fair_id["value"])
            )
            if not node.can_manage(farmer_object):
                fair_id["valid"] = False
                fair_id["message"] += (
                    "Cannot update farmer %s" % farmer_object.full_name
                )
                cell_obj = cells.Cell(heading="FairID", column="B")
                farmer_transaction["id"] = cell_obj.check_issue("id", fair_id)
        except Exception:
            pass
        return True

    def validate(self, node=None, supply_chain=None):
        """To validate farmer bulk excel rows."""
        response = super(FarmerWithTransactionExcel, self).validate()

        farmers_to_add = 0
        farmers_to_update = 0
        transactions_to_add = 0
        global_validity = True
        data_list = []
        for farmer_transaction in response["excel_data"]["row_data"]:
            farmer_statuses = []
            farmer_validity = True
            for field in self.Meta.farmer_fields:
                if field == self.Meta.farmer_fields[0]:
                    if farmer_transaction["id"]["value"]:
                        self._validate_fair_id(farmer_transaction, node)
                farmer_validity &= farmer_transaction[field]["valid"]
                farmer_statuses.append(farmer_transaction[field]["status"])
            if VALUE_CHANGED in farmer_statuses:
                farmers_to_update += 1
                farmer_status = VALUE_CHANGED
            elif set(farmer_statuses) == {VALUE_NEW}:
                farmers_to_add += 1
                farmer_status = VALUE_NEW
            else:
                farmer_status = VALUE_UNCHANGED
            farmer_transaction["farmer_status"] = farmer_status
            farmer_transaction["farmer_validity"] = farmer_validity
            transaction_validity = True
            has_trans = set(
                farmer_transaction[f]["status"]
                for f in [
                    "transaction_date",
                    "unit",
                    "currency",
                    "price_per_unit",
                    "quantity",
                ]
            )
            if has_trans != {VALUE_UNCHANGED}:
                transaction_status = VALUE_NEW
                transactions_to_add += 1
            else:
                transaction_status = VALUE_UNCHANGED
            for field in [
                "transaction_date",
                "unit",
                "currency",
                "price_per_unit",
                "quantity",
            ]:
                if not farmer_transaction["id"]["value"]:
                    transaction_validity &= farmer_transaction[field]["valid"]
                if (
                    transaction_status == VALUE_NEW
                    or transaction_status == VALUE_CHANGED
                ):
                    if farmer_transaction[field]["status"] == VALUE_UNCHANGED:
                        farmer_transaction[field]["status"] = VALUE_CHANGED
                        farmer_transaction[field]["valid"] = False
                        transaction_validity = False
                    elif farmer_transaction[field]["status"] == VALUE_CHANGED:
                        transaction_validity &= farmer_transaction[field][
                            "valid"
                        ]
                else:
                    farmer_transaction[field]["valid"] = True
                    if (
                        farmer_status == VALUE_CHANGED
                        or farmer_status == VALUE_NEW
                        and transaction_status == VALUE_UNCHANGED
                    ):
                        farmer_transaction[field]["valid"] = False
                        transaction_validity = False

            pid = comm_lib._decode(farmer_transaction["product_id"]["value"])
            if not pid or not Product.objects.filter(id=pid).exists():
                farmer_transaction["product_id"]["status"] = VALUE_CHANGED
                farmer_transaction["product_id"]["valid"] = False
                farmer_transaction["product_id"][
                    "message"
                ] += "Product not found. "
            farmer_transaction["transaction_status"] = transaction_status
            farmer_transaction["transaction_validity"] = transaction_validity

            farmer_transaction["valid"] = (
                farmer_validity and transaction_validity
            )
            farmer_transaction["is_duplicate"] = False
            farmer_transaction["duplicate_id"] = None
            farmer_transaction["duplicate_type"] = None

            if farmer_transaction["valid"]:
                # check transaction is duplicate or not.
                (
                    farmer_transaction["is_duplicate"],
                    farmer_transaction["duplicate_id"],
                    farmer_transaction["duplicate_type"],
                ) = self.check_duplicate_txn(farmer_transaction)

            if (
                farmer_status is not VALUE_UNCHANGED
                or transaction_status is not VALUE_UNCHANGED
            ):
                data_list.append(farmer_transaction)
            if farmer_transaction["is_duplicate"]:
                if farmer_transaction not in data_list:
                    data_list.append(farmer_transaction)
                farmer_transaction["valid"] = False
        # check double entry
        self.check_double_entry(data_list)
        for farmer_transaction in data_list:
            global_validity &= farmer_transaction["valid"]

        # # sort farmer list by validity
        # farmer_list = sorted(data_list, key=lambda i: i['valid'])
        excel_data = []
        for data in data_list:
            fields_dict = {
                "fields": [],
                "is_keep": False,
                "is_select": False,
                "is_removed": False,
                "is_new_farmer": False,
                "is_new_transaction": False,
                "is_farmer_updated": False,
            }
            for field in self.Meta.farmer_fields:
                data[field]["key"] = field
                fields_dict["fields"].append(data.pop(field, None))
            for field in self.Meta.transaction_fields:
                data[field]["key"] = field
                fields_dict["fields"].append(data.pop(field, None))
            for key, value in data.items():
                fields_dict[key] = value
            excel_data.append(fields_dict)

        response["excel_data"]["row_data"] = excel_data
        response["farmers_to_add"] = farmers_to_add
        response["farmers_to_update"] = farmers_to_update
        response["transactions_to_add"] = transactions_to_add
        response["count"] = len(data_list)
        response["valid"] = global_validity
        response["message"] = ""
        return response

    def check_duplicate_txn(self, txn):
        """Function to check transaction is already exists or not.

        Request Params:
            txn(dict)   :transaction data
        Response:
            is_duplicate(bool)          :true or false value.
            duplicate_txn_id(idencode)  :duplicate txn id.
        """
        price_per_unit = comm_lib.convert_float(txn["price_per_unit"]["value"])
        quantity = comm_lib.convert_float(txn["quantity"]["value"])

        # check duplicate external transaction or bulk excel
        # transactions exists or not.
        external_trans = ExternalTransaction.objects.filter(
            result_batches__product__name=txn["product"]["value"],
            price=(price_per_unit),
            result_batches__current_quantity=quantity,
            date__date=comm_lib._string_to_datetime(
                txn["transaction_date"]["value"]
            ),
            currency=txn["currency"]["value"],
            source__id=comm_lib._decode(txn["id"]["value"]),
            source__nodesupplychain__primary_operation__id=comm_lib._decode(
                txn["primary_operation"]["value"]
            ),
        )

        if not txn["id"]["value"]:
            dial_code = re.sub("[(),a-z,A-Z]", "", txn["dial_code"]["value"])
            phone_number = str(dial_code) + str(txn["phone"]["value"])
            farmer_dup = Farmer.objects.filter(
                first_name=txn["first_name"]["value"],
                last_name=txn["last_name"]["value"],
                street=txn["street"]["value"],
                city=txn["city"]["value"],
                country=txn["country"]["value"],
                province=txn["province"]["value"],
                zipcode=txn["zipcode"]["value"],
                email=txn["email"]["value"],
                nodesupplychain__primary_operation__id=comm_lib._decode(
                    txn["primary_operation"]["value"]
                ),
                identification_no=txn["identification_no"]["value"],
                phone=phone_number,
            )
            # check if duplicate transaction or farmer exists
            if farmer_dup:
                return True, farmer_dup[0].idencode, DUPLICATE_FARMER
        if external_trans:
            return True, external_trans[0].idencode, DUPLICATE_EX_TXN
        return False, None, None

    def check_double_entry(self, txn):
        """Function for check double entry of transaction details in excel."""
        seen_list = []
        for farmer_transaction in txn:
            double_entry = {"double_entry": False, "index": ""}
            txn_dict = {}
            for field in self.Meta.farmer_fields:
                txn_dict[field] = farmer_transaction[field]["value"]
            for field in self.Meta.transaction_fields:
                txn_dict[field] = farmer_transaction[field]["value"]
            # double entry check only when txn details are valid
            if not farmer_transaction["valid"]:
                farmer_transaction["double_entry"] = double_entry
                continue
            if txn_dict in seen_list:
                index_val = seen_list.index(txn_dict)
                double_entry = {"double_entry": True, "index": index_val}
                farmer_transaction["valid"] = False
            seen_list.append(txn_dict)
            farmer_transaction["double_entry"] = double_entry
        return True
