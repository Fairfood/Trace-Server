import copy

from django.db import transaction as db_transaction

from v2.bulk_uploads.tasks.base import DataSheetAdapted
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.transactions import constants
from v2.transactions.serializers.external import ExternalTransactionSerializer


class BulkTransactionAdapter(DataSheetAdapted):
    """
    Adapter for formatting and creating bulk transaction data from a data
    sheet.
    """

    def format_data(self):
        """
        Format the data sheet's data for bulk transaction creation.

        This method prepares the data from the data sheet for bulk transaction
        creation. It adds common data to each transaction entry and performs
        validation checks.

        It modifies `self.data` in place with the formatted data.
        """

        data_sheet = self.data_sheet
        data = copy.deepcopy(data_sheet.data)
        common_data = {
            "product": data_sheet.product.idencode,
            "unit": data_sheet.unit,
            "currency": data_sheet.currency,
            "force_create": True,
            "type": constants.EXTERNAL_TRANS_TYPE_INCOMING
        }

        farmers = data_sheet.node.get_supplier_chain(
            data_sheet.product.supply_chain)[0].filter(
            type=NODE_TYPE_FARM)
        id_farmers = dict((f.identification_no, f)
                          for f in farmers if f.identification_no)

        for idx, value in data.items():
            # Validate identification numbers
            if value.get('identification_no') not in id_farmers:
                self.errors[idx].update(
                    {"identification_no": 'Invalid identification number'})
                continue
            # Add common data to each entry
            value["node"] = id_farmers[value["identification_no"]]
            value.update(common_data)
            self.data[idx] = value

    @db_transaction.atomic()
    def create_data(self):
        """
        Create bulk transactions from the formatted data.

        This method uses the ExternalTransactionSerializer to create bulk
        transactions using the formatted data. It handles validation and error
        handling.

        It iterates through the formatted data and attempts to create each
        transaction. If a transaction fails validation, errors are collected
        and stored.

        Note: This method modifies self.errors if there are errors during
            creation.
        """

        serializer_klass = ExternalTransactionSerializer
        for idx, value in self.data.items():
            try:
                serializer = serializer_klass(
                    data=value,
                    context={
                        "node": self.data_sheet.node,
                        "user": self.data_sheet.creator,
                        "data_sheet": self.data_sheet,
                    },
                )
                if not serializer.is_valid():
                    self.errors[idx].update(serializer.errors)
                    continue
                transaction = serializer.save()
                self.data_sheet.added_transactions.add(transaction)
            except Exception as e:
                self.exceptions.append(e)

