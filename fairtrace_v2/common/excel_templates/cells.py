from datetime import datetime

from common import library as comm_lib
from common.country_data import COUNTRY_LIST
from common.currencies import CURRENCY_CHOICES
from v2.transactions.choices import FieldType

from .constants import VALUE_CHANGED
from .constants import VALUE_NEW
from .constants import VALUE_UNCHANGED


class Cell:
    """Class to handle Cell and functions."""

    heading = ""
    column = ""
    cell = ""
    value = None
    required = True
    read = True
    write = False
    update = True
    hidden = False
    model_object = None
    database_value = None
    source = None

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        try:
            if "heading" in kwargs:
                self.heading = kwargs["heading"]
            else:
                self.heading = self.__class__.__name__.title()
            if "column" in kwargs:
                self.column = kwargs["column"]
            elif "cell" in kwargs:
                self.cell = kwargs["cell"]
            else:
                raise AttributeError(
                    "Either 'cell' or 'column' should be implemented when"
                    " implementing %s." % self.__class__.__name__
                )
            if "required" in kwargs:
                self.required = kwargs["required"]
            if "read" in kwargs:
                self.read = kwargs["read"]
            if "write" in kwargs:
                self.write = kwargs["write"]
            if "hidden" in kwargs:
                self.hidden = kwargs["hidden"]
            if "database_value" in kwargs:
                self.database_value = kwargs["database_value"]
            if "source" in kwargs:
                self.source = kwargs["source"]
            if "update" in kwargs:
                self.update = kwargs["update"]

        except KeyError as key:
            raise AttributeError(
                "%s must be provided when implementing %s",
                (", ".join(key.args), self.__class__.__name__),
            )

    def __str__(self):
        """To perform function __str__."""
        return "%s" % self.value

    def set_value(self, value):
        """To perform function set_value."""
        if type(value) == str:
            # if value is country then convert first letter
            # to uppercase.
            if value.capitalize() in COUNTRY_LIST:
                value = value.capitalize()
        self.value = value

    @property
    def to_representation(self):
        """To perform function to_representation."""
        return self.value

    def check_issue(self, heading, check):
        """To perform function check_issue."""
        txn_fields = [
            "Transaction Date",
            "Unit",
            "Currency",
            "Product",
            "Price per unit",
            "Total quantity",
        ]
        check["issues"]["total"] = 1
        if heading in txn_fields:
            check["issues"]["transaction_issues"] = 1
        else:
            check["issues"]["farmer_issues"] = 1
        return check

    def is_farmer_data(self, heading):
        """To perform function is_farmer_data."""
        txn_fields = [
            "Transaction Date",
            "Unit",
            "Currency",
            "Product ID",
            "Product",
            "Price per unit",
            "Total quantity",
        ]
        if heading in txn_fields:
            return False
        else:
            return True

    def validate(self):
        """To perform function validate."""
        if not self.model_object and self.update:
            status = VALUE_NEW
        elif not self.database_value and not self.value:
            status = VALUE_UNCHANGED
        elif self.database_value == self.value:
            status = VALUE_UNCHANGED
        else:
            status = VALUE_CHANGED

        data = {
            "label": self.heading,
            "value": self.to_representation,
            "required": self.required,
            "status": status,
            "old_value": self.database_value,
            "new_value": self.to_representation,
            "valid": True,
            "message": "",
            "issues": {
                "total": 0,
                "transaction_issues": 0,
                "farmer_issues": 0,
            },
            "is_farmer_data": self.is_farmer_data(self.heading),
        }

        if self.required and not self.value:
            data["valid"] = False
            data["message"] += "%s is mandatory. " % self.heading
            data = self.check_issue(self.heading, data)
        return data


class AlphaCell(Cell):
    """Class to handle AlphaCell and functions."""

    def validate(self):
        """To perform function validate."""
        check = super(AlphaCell, self).validate()
        check["type"] = None
        if check["valid"] and not self.value.isalpha():
            check["valid"] = False
            check["message"] += "%s should be a alphabetical. " % self.heading
            check = self.check_issue(self.heading, check)
        return check


class CharCell(Cell):
    """Class to handle CharCell and functions."""

    def set_value(self, value):
        """To perform function set_value."""
        if value:
            value = str(value)
            value = value.strip()
        self.value = value

    def validate(self):
        """To perform function validate."""
        check = super(CharCell, self).validate()
        check["type"] = FieldType.STRING.value
        if not check["valid"]:
            return check
        try:
            str(self.value)
            check["valid"] = True
            check["value"] = self.to_representation
        except Exception:
            check["valid"] = False
            check["value"] = self.to_representation
            check["message"] += "%s should be a string. " % self.heading
            check = self.check_issue(self.heading, check)

        return check


class IntegerCell(Cell):
    """Class to handle IntegerCell and functions."""

    def validate(self):
        """To perform function validate."""
        check = super(IntegerCell, self).validate()
        check["type"] = FieldType.NUMBER.value
        if not check["valid"]:
            return check
        try:
            if not self.value and not self.required:
                value = ""
            else:
                self.value = str(self.value).replace(" ", "")
                value = int(self.value)
            check["valid"] = True
            check["value"] = value
        except Exception:
            check["valid"] = False
            check["value"] = self.value
            check["message"] += "%s should be an integer. " % self.heading
            check = self.check_issue(self.heading, check)
        return check


class DateCell(Cell):
    """Class to handle DateCell and functions."""

    min_date = None
    max_date = None
    supported_formats = ("%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y")

    def __init__(self, min_date=None, max_date=None, *args, **kwargs):
        """To perform function __init__."""
        Cell.__init__(self, *args, **kwargs)
        if min_date:
            self.min_date = datetime.strptime(min_date, "%d-%m-%Y")
        if max_date:
            self.max_date = datetime.strptime(max_date, "%d-%m-%Y")

    def set_value(self, value):
        """To perform function set_value."""
        # if type(value) == str:
        for fmt in self.supported_formats:
            try:
                value = datetime.strptime(str(value), fmt)
                break
            except ValueError:
                pass
        self.value = value

    @property
    def to_representation(self):
        """To perform function to_representation."""
        if self.value:
            try:
                return self.value.strftime("%d-%m-%Y")
            except Exception:
                return None

    def validate(self):
        """To perform function validate."""
        check = super(DateCell, self).validate()
        check["type"] = FieldType.DATE.value
        if not check["valid"]:
            return check
        if not self.value and not self.required:
            return check
        check["value"] = self.to_representation
        if not check["value"]:
            check["valid"] = False
            check["message"] += "Invalid format for %s. " % self.heading
            check = self.check_issue(self.heading, check)
            return check
        if type(self.value) == str:
            check["valid"] = False
            check["message"] += "Invalid format for %s. " % self.heading
            check = self.check_issue(self.heading, check)
            return check
        if self.min_date:
            if self.value < self.min_date:
                check["valid"] = False
                check["message"] += "%s should be greater than %s. " % (
                    self.heading,
                    self.min_date.strftime("%d-%m-%Y"),
                )
                check = self.check_issue(self.heading, check)
        if self.max_date:
            if self.value > self.max_date:
                check["valid"] = False
                check["message"] += "%s should be lesser than %s. " % (
                    self.heading,
                    self.max_date.strftime("%d-%m-%Y"),
                )
                check = self.check_issue(self.heading, check)
        return check


class FloatCell(Cell):
    """Class to handle FloatCell and functions."""

    def validate(self):
        """To perform function validate."""
        check = super(FloatCell, self).validate()
        check["type"] = FieldType.NUMBER.value
        if not check["valid"]:
            return check
        try:
            if not self.value and not self.required:
                value = None
            else:
                self.value = str(self.value).replace(" ", "")
                value = float(self.value)
            check["valid"] = True
            check["value"] = value
        except Exception:
            check["valid"] = False
            check["value"] = self.value
            check["message"] += "%s should be a decimal. " % self.heading
            check = self.check_issue(self.heading, check)
        return check


class ChoiceCell(Cell):
    """Class to handle ChoiceCell and functions."""

    choices: list = []

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        try:
            self.choices = kwargs["choices"]
        except KeyError as key:
            raise AttributeError(
                "%s must be provided when implementing %s",
                (key, self.__class__.__name__),
            )
        Cell.__init__(self, *args, **kwargs)

    def validate(self):
        """To perform function validate."""
        check = super(ChoiceCell, self).validate()
        check["type"] = FieldType.CHOICE.value
        if not check["valid"]:
            return check
        if (self.value or self.required) and (self.value not in self.choices):
            check["valid"] = False
            check["message"] += "%s is not a valid %s. " % (
                self.value,
                self.heading,
            )
            check = self.check_issue(self.heading, check)
        # Commented out because of faulty logic.
        # if self.value:
        #     raise Exception(self.value)
        return check


class EmailCell(CharCell):
    """Class to handle EmailCell and functions."""

    def set_value(self, value):
        """To perform function set_value."""
        if value:
            value = str(value)
            value = value.strip()
        self.value = value

    def validate(self):
        """To perform function validate."""
        check = super(EmailCell, self).validate()
        check["type"] = FieldType.EMAIL.value
        if not check["valid"]:
            return check
        if not self.required and not self.value:
            check["valid"] = True
            check["value"] = self.value
        else:
            valid, message = comm_lib._validate_email(self.value)
            if not valid:
                check["valid"] = False
                check["message"] += "Invalid email address. "
                check = self.check_issue(self.heading, check)
        return check


class PhoneNumberCell(Cell):
    """Class to handle PhoneNumberCell and functions."""

    def set_value(self, value):
        """To perform function set_value."""
        if not value.startswith("+"):
            value = "+%s" % value
        self.value = value

    def validate(self):
        """To perform function validate."""
        check = super(PhoneNumberCell, self).validate()
        check["type"] = FieldType.NUMBER.value
        if not check["valid"]:
            return check
        value = comm_lib._validate_phone(self.value)
        check["value"] = value
        if not value:
            check["valid"] = False
            check["value"] = self.to_representation
            check["message"] += "Invalid phone number. "
            check = self.check_issue(self.heading, check)
        return check


class DependantChoiceCell(Cell):
    """Class to handle DependantChoiceCell and functions."""

    selection = None
    choices: list = []

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        try:
            self.choices = kwargs["choices"]
            self.selection = kwargs["selection"]
        except KeyError as key:
            raise AttributeError(
                "%s must be provided when implementing %s",
                (key, self.__class__.__name__),
            )
        Cell.__init__(self, *args, **kwargs)

    def validate(self, **kwargs):
        """To perform function validate."""
        check = super(DependantChoiceCell, self).validate()
        check["type"] = FieldType.CHOICE.value
        if not check["valid"]:
            return check
        if "selection" not in kwargs:
            raise AttributeError(
                "selection needs to be passed when validating"
                " DependantChoiceCell"
            )
        selection = kwargs["selection"]
        if (
            selection.value not in self.choices
            or self.value not in self.choices[selection.value]
        ):
            check["valid"] = False
            check["value"] = self.to_representation
            check[
                "message"
            ] += "%s is not a valid %s for the selected %s. " % (
                self.value,
                self.heading,
                selection.heading,
            )
            check = self.check_issue(self.heading, check)
        return check


class CombinationCells(Cell):
    """Class to handle CombinationCells and functions."""

    cells: list = []
    combined_cell_type = Cell
    deliminator = ""

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        try:
            self.cells = kwargs["cells"]
            self.combined_cell_type = kwargs["combined_cell_type"]
            if "deliminator" in kwargs:
                self.deliminator = kwargs["deliminator"]
        except KeyError as key:
            raise AttributeError(
                "%s must be provided when implementing %s",
                (key, self.__class__.__name__),
            )
        Cell.__init__(self, *args, **kwargs)

    def validate(self):
        """To perform function validate."""
        check = super(CombinationCells, self).validate()
        check["type"] = None
        if not check["valid"]:
            return check
        value = self.deliminator.join([str(i.value) for i in self.cells])
        base_cell = self.combined_cell_type(heading=self.heading, column="")
        base_cell.set_value(value)
        return base_cell.validate()


class PhoneCell(Cell):
    """Class to handle PhoneCell and functions."""

    def set_value(self, value):
        """To perform function set_value."""
        if value:
            value = str(value).replace(" ", "")
            value = str(value).replace("-", "")
        self.value = value

    def validate(self):
        """To perform function validate."""
        check = super(PhoneCell, self).validate()
        check["type"] = FieldType.NUMBER.value
        if not check["valid"]:
            return check
        try:
            if self.value:
                check["value"] = int(self.value)
        except Exception:
            check["valid"] = False
            check["value"] = self.to_representation
            check["message"] += "Invalid phone number. "
            check = self.check_issue(self.heading, check)
        return check


class DialCodeCell(ChoiceCell):
    """Class to handle DialCodeCell and functions."""

    @property
    def to_representation(self):
        """To perform function to_representation."""
        if self.value:
            return self.value.split("(")[-1].split(")")[0]
        else:
            return self.value


class CurrencyCell(CharCell):
    """Class to handle CurrencyCell and functions."""

    def validate(self):
        """To perform function validate."""
        check = super(CurrencyCell, self).validate()
        check["type"] = FieldType.CHOICE.value
        if not check["valid"]:
            return check
        if self.value:
            if not any(
                self.value in currency for currency in CURRENCY_CHOICES
            ):
                check["valid"] = False
                check["value"] = self.to_representation
                check["message"] += "%s is not a valid choice." % self.value
                check = self.check_issue(self.heading, check)
        return check


class CountryCell(ChoiceCell):
    """Class to handle CountryCell and functions."""

    def validate(self):
        """To perform function validate."""
        check = super(CountryCell, self).validate()
        check["type"] = FieldType.CHOICE.value
        if not check["valid"]:
            return check
        if self.value:
            if not any(self.value in country for country in COUNTRY_LIST):
                check["valid"] = False
                check["value"] = self.to_representation
                check["message"] += "%s is not a valid choice." % self.value
                check = self.check_issue(self.heading, check)
        return check
