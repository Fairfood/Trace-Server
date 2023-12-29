import copy

from django.apps import apps
from django.db import transaction as db_transaction

from common.library import decode, encode
from v2.bulk_uploads.schemas.transaction_upload_schema import (
    TransactionUploadSchema, )
from v2.bulk_uploads.tasks.base import DataSheetAdapted
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Operation
from v2.supply_chains.serializers.node import FarmerSerializer
from v2.supply_chains.serializers.supply_chain import FarmerInviteSerializer
from v2.transactions import constants
from v2.transactions.serializers.external import ExternalTransactionSerializer


class BulkTraceAdapter(DataSheetAdapted):
    """
    Adapter for formatting and creating bulk transaction data from a data
    sheet.
    """

    def __init__(self, data_sheet):
        super().__init__(data_sheet)
        self.farmers_ids = []

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
        connection_common_data = {
            "node": data_sheet.node,
            "supply_chain": data_sheet.supply_chain,
            "user": data_sheet.creator,
        }
        txn_common_data = {
            "product": (data_sheet.product.idencode
                        if data_sheet.product else None),
            "unit": data_sheet.unit,
            "currency": data_sheet.currency,
            "force_create": True,
            "type": constants.EXTERNAL_TRANS_TYPE_INCOMING
        }

        farmer_pks = [decode(_value['fair_id'])
                      for _value in data.values()
                      if "fair_id" in _value]

        self.farmers_ids = data_sheet.node.get_supplier_chain(
            data_sheet.supply_chain)[0].filter(
            type=NODE_TYPE_FARM, pk__in=farmer_pks
        ).values_list("id", flat=True)

        for idx, value in data.items():
            # Add common data to each entry
            connection_type = value.pop("connection_type", None)
            country_code = value.pop("country_code", None)
            fair_id = value.get("fair_id", None)
            family_members = value.pop("family_members", None)

            if family_members:
                value["family_members"] = int(family_members)

            if fair_id and decode(fair_id) not in self.farmers_ids:
                self.errors[idx].update(
                    {"fair_id": 'Invalid fair id'})
                continue

            if connection_type:
                # Query the Operation model to find the primary operation
                # based on the connection_type
                primary_operation = Operation.objects.filter(
                    name__iexact=connection_type.strip(),
                    supply_chains=data_sheet.supply_chain,
                    node_type=NODE_TYPE_FARM
                ).last()

                if not primary_operation:
                    primary_operation = Operation.objects.filter(
                        supply_chains=data_sheet.supply_chain,
                        node_type=NODE_TYPE_FARM
                    ).last()

                if primary_operation:
                    # If a primary operation is found, assign its idencode to
                    # the value dictionary
                    value["primary_operation"] = primary_operation.idencode
                else:
                    # If no primary operation is found, set an error message
                    self.errors[idx][
                        "connection_type"] = "Invalid connection type"

                # Add country code to phone number
            if country_code and "phone" in value:
                value["phone"] = f"{country_code}{value['phone']}"

            # Get the list of fields in the TransactionUploadSchema
            transaction_fields = list(TransactionUploadSchema
                                      .get_fields().keys())

            (transaction_fields.remove("identification_no") if
             "identification_no" in transaction_fields else None)

            # Create the 'transaction_data' dictionary using a dictionary
            # comprehension
            transaction_data = {
                field: value.pop(field) for field in transaction_fields if
                field in value
            }

            # Check if all mandatory fields are present in the transaction
            # data.
            quantity = transaction_data.get("quantity", 0.0)

            if quantity > 0:
                # Update the 'transaction_data' dictionary with common
                # transaction data
                transaction_data.update(txn_common_data)
                value["transaction_data"] = transaction_data

            # Add the connection common data to the value dictionary
            value.update(connection_common_data)
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
        farmer_model = apps.get_model("supply_chains", "Farmer")

        # map farmer idencode to
        farmer_idencode_to_obj = dict([
            (encode(farmer.pk), farmer)
            for farmer
            in farmer_model.objects.filter(pk__in=self.farmers_ids)])

        farmer_serializer_klass = FarmerInviteSerializer
        transaction_serializer_klass = ExternalTransactionSerializer
        update_serializer_klass = FarmerSerializer

        for idx, value in self.data.items():
            try:
                transaction_data = value.pop("transaction_data", None)

                if value.get("fair_id", None):
                    # Update farmer if fair_id is present
                    farmer = farmer_idencode_to_obj.get(value["fair_id"])

                    if not farmer:
                        continue

                    serializer = update_serializer_klass(
                        farmer,
                        data=value,
                        partial=True,
                        context={
                            "node": self.data_sheet.node,
                            "user": self.data_sheet.creator,
                        },
                    )
                    serializer.is_valid(raise_exception=True)
                    farmer = serializer.save()

                else:
                    serializer = farmer_serializer_klass(
                        data=value,
                        context={
                            "node": self.data_sheet.node,
                            "user": self.data_sheet.creator,
                        },
                    )
                    serializer.is_valid(raise_exception=True)
                    obj = serializer.save()
                    farmer = obj.invitee

                if transaction_data:
                    transaction_data["node"] = farmer.idencode
                    serializer = transaction_serializer_klass(
                        data=transaction_data,
                        context={
                            "node": self.data_sheet.node,
                            "user": self.data_sheet.creator,
                            "data_sheet": self.data_sheet,
                        },
                    )
                    if not serializer.is_valid():
                        self.errors[idx].update(serializer.errors)
                        continue
                    serializer.save()
            except Exception as e:
                self.exceptions.append(e)
