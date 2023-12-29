from datetime import datetime
from typing import Any
from typing import Dict
from typing import Optional

import pandera as pa
from pandera.typing import Series

from v2.bulk_uploads.schemas.base import BaseUploadSchema
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Node, SupplyChain


class TransactionUploadSchema(BaseUploadSchema):
    """Schema for uploading transaction-related data.

    This schema inherits from the FarmerUploadSchema and adds optional fields
    specific to transactions.

    Fields:
        date (pd.Timestamp): Required field for the date of the
                             transaction. It must contain values of
                             type pd.Timestamp.
        price (Optional[float]): Optional field for the price associated with
                                 the transaction. It allows any numeric value
                                 or None.
        quantity (Optional[float]): Optional field for the quantity associated
                                     with the transaction. It allows any
                                     numeric value or None.
        invoice_no (Optional[str]): Optional field for the invoice number
                                    related to the transaction. It allows any
                                    value or None.
    """
    date: Series[datetime] = pa.Field(coerce=True)
    price: Series[pa.Float] = pa.Field(gt=0, coerce=True)
    quantity: Series[pa.Float] = pa.Field(coerce=True, gt=0)
    identification_no: Series[str] = pa.Field(coerce=True, ne="")
    invoice_number: Optional[Series[str]] = pa.Field(coerce=True)
    buyer_ref_number: Optional[Series[str]] = pa.Field(coerce=True)
    seller_ref_number: Optional[Series[str]] = pa.Field(coerce=True)

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

    @pa.check("date",
              name="date_check",
              error="Dates in the future are not allowed.",
              element_wise=True)
    def date_check(cls, transaction_date: datetime) -> bool:
        """Check if the transaction date is valid.

        This class method checks if the transaction date is valid. The
        transaction date is valid if it is not in the future.

        Args:
            transaction_date (datetime): The transaction date to check.

        Returns:
            bool: True if the transaction date is valid, False otherwise.
        """
        return transaction_date <= datetime.today()

    @pa.check("identification_no",
              name="identification_no_check",
              error="Identification number is not valid.",
              element_wise=True)
    def identification_no_check(cls, identification_no: str) -> bool:
        """ Check if the identification number is valid.

        This class method checks if the identification number is valid. The
        identification number is valid if it is in the list of valid
        identification numbers.

        Args:
            identification_no (str): The identification number to check.

        Returns:
            bool: True if the identification number is valid, False otherwise.
        """

        ids = cls.get_schema_metadata().get('ids', [])
        return identification_no in ids
