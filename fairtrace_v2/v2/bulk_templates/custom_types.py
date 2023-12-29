"""Define your custom types like  Farmer id, reg number."""
from common import library as comm_lib
from common.currencies import CURRENCY_CHOICES
from v2.products import constants as prod_constants
from v2.supply_chains.models import Farmer


class FarmerId(str):
    """Custom type for FarmerId."""

    value = None

    def __new__(cls, value):
        """Construct new value type."""
        ob = super(FarmerId, cls).__new__(cls, value)
        # do validation here
        ob.value = ob
        ob._validate()
        return ob

    def _validate(self):
        """To perform function _validate."""
        # decode to int and verify if it exists in db
        # raise ValueError('value must be 10')
        try:
            Farmer.objects.get(id=comm_lib._decode(self.value))
        except Exception:
            raise ValueError("Invalid FarmerId")

        pass

    @property
    def to_id(self):
        """decade value."""
        return comm_lib._decode(self.value)


class TraceId(str):
    """Custom type from TraceId."""

    value = None

    def __new__(cls, value):
        """Construct new value type."""
        if value is None:
            return value
        ob = super(TraceId, cls).__new__(cls, value)
        # do validation here
        ob.value = ob
        ob._validate()
        return ob

    def _validate(self):
        """To perform function _validate."""
        # verify if it exists in db
        # raise ValueError('
        farmer = Farmer.objects.filter(identification_no=self.value)
        if not farmer:
            raise ValueError("Invalid identification no")
        pass


class Currency(str):
    """Custom type for Currency."""

    value = None

    def __new__(cls, value):
        """Construct new value type."""
        ob = super(Currency, cls).__new__(cls, value)
        # do validation here
        ob.value = ob
        ob._validate()
        return ob

    def _validate(self):
        """To perform function _validate."""
        try:
            if not self.value:
                raise ValueError("Invalid Choice")
            if not any(
                self.value in currency for currency in CURRENCY_CHOICES
            ):
                raise ValueError("Invalid Choice")
        except Exception:
            raise ValueError("Invalid Choice")

        pass


class Unit(str):
    """Custom type called Unit."""

    value = None

    def __new__(cls, value):
        """Construct new value type."""
        ob = super(Unit, cls).__new__(cls, value)
        # do validation here
        ob.value = ob
        ob._validate()
        return ob

    def _validate(self):
        """To perform function _validate."""
        try:
            if not self.value:
                raise ValueError("Invalid Choice")
            if not any(
                self.value in unit for unit in prod_constants.UNIT_CHOICES
            ):
                raise ValueError("Invalid Choice")
        except Exception:
            raise ValueError("Invalid Choice")

        pass
