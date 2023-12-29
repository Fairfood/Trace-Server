import re

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
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Operation

try:
    FARM_OPERATION_CHOICES = [
        o.name for o in Operation.objects.filter(node_type=NODE_TYPE_FARM)
    ]
except ProgrammingError:
    FARM_OPERATION_CHOICES = []


class FarmerInviteExcelRow(ExcelRow):
    """Class to handle FarmerInviteExcelRow and functions."""

    first_name = cells.CharCell(heading="First Name", column="B")
    last_name = cells.CharCell(heading="Last Name", column="C")
    primary_operation = cells.ChoiceCell(
        heading="Farm Type", column="D", choices=FARM_OPERATION_CHOICES
    )
    identification_no = cells.CharCell(
        heading="Identification number", column="E", required=False
    )

    street = cells.CharCell(heading="Street Name", column="F", required=False)
    city = cells.CharCell(heading="City/Village", column="G", required=False)
    country = cells.CountryCell(
        heading="Country", column="H", choices=COUNTRY_LIST
    )
    province = cells.DependantChoiceCell(
        heading="Province",
        column="I",
        choices=COUNTRY_WITH_PROVINCE,
        selection="country",
    )
    zipcode = cells.CharCell(heading="Postal code", column="J", required=False)

    dial_code = cells.ChoiceCell(
        heading="Country Code",
        column="K",
        choices=DIAL_CODES_WITH_NAME,
        required=False,
    )
    phone = cells.IntegerCell(
        heading="Contact Number", column="L", required=False
    )
    email = cells.EmailCell(heading="Email", column="M", required=False)
    latitude = cells.FloatCell(heading="Latitude", column="N", required=False)
    longitude = cells.FloatCell(
        heading="Longitude", column="O", required=False
    )

    class Meta:
        name = "farmers"
        fields = [
            "first_name",
            "last_name",
            "primary_operation",
            "identification_no",
            "street",
            "city",
            "country",
            "province",
            "zipcode",
            "dial_code",
            "phone",
            "email",
            "latitude",
            "longitude",
        ]


class FarmerInviteExcel(Excel):
    """Class to handle FarmerInviteExcel and functions."""

    class Meta:
        first_row = 6
        row_class = FarmerInviteExcelRow
        data_sheet = "datasheets"
        fields = []
        mandatory_column = "C"


class FarmerExportExcelRow(ExcelRow):
    """Class to handle FarmerExportExcelRow and functions."""

    first_name = cells.CharCell(column="B", read=False, write=True)
    last_name = cells.CharCell(column="C", read=False, write=True)
    gender = cells.CharCell(column="D", read=False, write=True)
    dob = cells.CharCell(column="E", read=False, write=True)
    primary_operation = cells.CharCell(column="F", read=False, write=True)
    identification_no = cells.CharCell(column="G", read=False, write=True)

    street = cells.CharCell(column="H", read=False, write=True)
    city = cells.CharCell(column="I", read=False, write=True)
    province = cells.CharCell(column="J", read=False, write=True)
    country = cells.CharCell(column="K", read=False, write=True)
    zipcode = cells.CharCell(column="L", read=False, write=True)
    birth_city = cells.CharCell(column="M", read=False, write=True)

    description_basic = cells.CharCell(column="N", read=False, write=True)
    marital_status = cells.CharCell(column="O", read=False, write=True)
    family_members = cells.IntegerCell(column="P", read=False, write=True)
    farm_area = cells.CharCell(column="Q", read=False, write=True)
    income_from_main_product = cells.FloatCell(
        column="R", read=False, write=True
    )
    income_from_other_sources = cells.CharCell(
        column="S", read=False, write=True
    )

    phone = cells.CharCell(column="T", read=False, write=True)
    email = cells.CharCell(column="U", read=False, write=True)
    latitude = cells.FloatCell(column="V", read=False, write=True)
    longitude = cells.FloatCell(column="W", read=False, write=True)

    class Meta:
        name = "farmers"
        fields = [
            "first_name",
            "last_name",
            "gender",
            "dob",
            "primary_operation",
            "identification_no",
            "street",
            "city",
            "province",
            "country",
            "zipcode",
            "birth_city",
            "description_basic",
            "marital_status",
            "family_members",
            "farm_area",
            "income_from_main_product",
            "income_from_other_sources",
            "phone",
            "email",
            "latitude",
            "longitude",
        ]


class FarmerExportExcel(Excel):
    """Class to handle FarmerExportExcel and functions."""

    class Meta:
        first_row = 3
        row_class = FarmerExportExcelRow
        data_sheet = "farmers"
        fields: list = []
        mandatory_column = "C"


class FarmerExcelRow(ExcelRow):
    """Class to handle FarmerExcelRow and functions."""

    id = cells.CharCell(
        heading="FairID",
        column="B",
        write=True,
        required=False,
        source="idencode",
    )
    first_name = cells.CharCell(heading="First Name", column="C", write=True)
    last_name = cells.CharCell(heading="Last Name", column="D", write=True)
    primary_operation = cells.ChoiceCell(
        heading="Connection Type",
        column="E",
        choices=FARM_OPERATION_CHOICES,
        write=True,
        source="primary_operation_name",
    )
    identification_no = cells.CharCell(
        heading="Registration number", column="F", required=False, write=True
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
        ]
        related_model = Farmer
        id_field = "id"


class FarmerExcel(Excel):
    """Class to handle FarmerExcel and functions."""

    class Meta:
        first_row = 8
        row_class = FarmerExcelRow
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

    def _validate_identification_no(self, farmer, node, sc):
        """To perform function _validate_identification_no."""
        id_no_data = farmer["identification_no"]
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
                farmer["identification_no"] = cell_obj.check_issue(
                    "identification_no", id_no_data
                )
        except Exception:
            pass
        return True

    def validate(self, node=None, supply_chain=None):
        """To validate farmer bulk excel rows."""
        response = super(FarmerExcel, self).validate()

        farmers_to_add = 0
        farmers_to_update = 0
        global_validity = True
        data_list = []
        message = ""
        for farmer in response["excel_data"]["row_data"]:
            if farmer["identification_no"]["value"]:
                self._validate_identification_no(farmer, node, supply_chain)
            farmer_statuses = []
            farmer_validity = True
            for field in self.Meta.farmer_fields:
                farmer_validity &= farmer[field]["valid"]
                message += farmer[field]["message"]
                farmer_statuses.append(farmer[field]["status"])
            if VALUE_CHANGED in farmer_statuses:
                farmers_to_update += 1
                farmer_status = VALUE_CHANGED
            elif set(farmer_statuses) == {VALUE_NEW}:
                farmers_to_add += 1
                farmer_status = VALUE_NEW
            else:
                farmer_status = VALUE_UNCHANGED
            farmer["farmer_status"] = farmer_status
            farmer["farmer_validity"] = farmer_validity
            # check farmer is duplicate or not.
            (
                farmer["is_duplicate"],
                farmer["duplicate_id"],
            ) = self.check_duplicate_farmer(farmer, node)
            if farmer_status is not VALUE_UNCHANGED:
                farmer["valid"] = farmer_validity
                data_list.append(farmer)
            if farmer["is_duplicate"]:
                farmer["valid"] = False

        # check double entry
        self.check_double_entry(data_list)
        for farmer in data_list:
            global_validity &= farmer["valid"]

        response["excel_data"]["row_data"] = data_list
        response["farmers_to_add"] = farmers_to_add
        response["farmers_to_update"] = farmers_to_update
        response["count"] = len(data_list)
        response["valid"] = global_validity
        response["message"] = message

        return response

    def check_duplicate_farmer(self, farmer, node):
        """Function to check farmer is already exists or not.

        Request Params:
            txn(dict)   :farmer data
        Response:
            is_duplicate(bool)          :true or false value.
            duplicate_farmer_id(id)     :duplicate Farmer id.
        """
        # check duplicate farmer exists or not.
        farmer_statuses = []
        for field in self.Meta.farmer_fields:
            farmer_statuses.append(farmer[field]["status"])

        if VALUE_CHANGED or VALUE_NEW in farmer_statuses:
            if not farmer["id"]["value"]:
                dial_code = re.sub(
                    "[(),a-z,A-Z]", "", farmer["dial_code"]["value"]
                )
                phone_number = str(dial_code) + str(farmer["phone"]["value"])
                farmer_dup = Farmer.objects.filter(
                    first_name=farmer["first_name"]["value"],
                    last_name=farmer["last_name"]["value"],
                    street=farmer["street"]["value"],
                    city=farmer["city"]["value"],
                    country=farmer["country"]["value"],
                    province=farmer["province"]["value"],
                    zipcode=farmer["zipcode"]["value"],
                    email=farmer["email"]["value"],
                    nodesupplychain__primary_operation__name=farmer[
                        "primary_operation"
                    ]["value"],
                    identification_no=farmer["identification_no"]["value"],
                    phone=phone_number,
                    managers=node,
                )
                # if duplicate farmer exists, pass the
                # farmer id.
                if farmer_dup:
                    return True, farmer_dup[0].idencode
        return False, None

    def check_double_entry(self, farmers):
        """Function for check double entry of farmer details in excel."""
        seen_list = []
        for farmer in farmers:
            farmer_dict = {}
            double_entry = {"double_entry": False, "index": ""}
            # double entry check only when farmer details are valid.
            if not farmer["valid"] and not farmer["is_duplicate"]:
                continue

            for field in self.Meta.farmer_fields:
                farmer_dict[field] = farmer[field]["value"]
            is_duplicate = False
            if farmer_dict in seen_list:
                is_duplicate = True
                index_val = seen_list.index(farmer_dict)
                double_entry = {"double_entry": True, "index": index_val}
                farmer["valid"] = False
            seen_list.append(farmer_dict)
            if not farmer["is_duplicate"]:
                farmer["is_duplicate"] = is_duplicate
            farmer["double_entry"] = double_entry
        return True
