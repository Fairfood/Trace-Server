from datetime import datetime
from typing import Optional

import pandas as pd
import pandera as pa
from pandera.typing import Series

from v2.bulk_uploads.schemas.farmer_upload_schema import FarmerUploadSchema


class TraceFarmerUploadSchema(FarmerUploadSchema):
    """Farmer upload schema model.

    This schema model represents the schema for uploading farmer data. It
    defines the structure and data types of the columns expected in the farmer
    data sheet.

    Attributes:
        fair_id (Optional[Series[str]]): The fair ID column in the data sheet.
    """
    fair_id: Optional[Series[str]] = pa.Field(nullable=True, coerce=True)

    @pa.check("identification_no",
              name="identification_no_check",
              error="Identification number already exists.",
              element_wise=True)
    def identification_no_check(cls, identification_no: str) -> bool:
        """Check if the identification number is valid."""
        return True


class TraceTransactionUploadSchema(TraceFarmerUploadSchema):
    """Farmer upload schema model.

    This schema model represents the schema for uploading farmer data. It
    defines the structure and data types of the columns expected in the farmer
    data sheet.

    Attributes:
        date (pd.Timestamp): Required field for the date of the
        transaction. It must contain values of type pd.Timestamp.
            price (Optional[float]): Optional field for the price associated
            with the transaction. It allows any numeric value or None.
        quantity (Optional[float]): Optional field for the quantity associated
            with the transaction. It allows any numeric value or None.
        invoice_number (Optional[str]): Optional field for the invoice number
            related to the transaction. It allows any value or None.
        buyer_ref_number (Optional[str]): Optional field for the buyer
            reference number related to the transaction. It allows any value or
            None.
        seller_ref_number (Optional[str]): Optional field for the seller
            reference number related to the transaction. It allows any value or
            None.
    """
    date: Series[datetime] = pa.Field(coerce=True)
    price: Series[pa.Float] = pa.Field(gt=0, coerce=True)
    quantity: Series[pa.Float] = pa.Field(coerce=True, gt=0)
    invoice_number: Optional[Series[str]] = pa.Field(
        coerce=True, nullable=True)
    buyer_ref_number: Optional[Series[str]] = pa.Field(
        coerce=True, nullable=True)
    seller_ref_number: Optional[Series[str]] = pa.Field(
        coerce=True, nullable=True)

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
