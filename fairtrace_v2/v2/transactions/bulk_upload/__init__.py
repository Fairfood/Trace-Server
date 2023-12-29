from common.library import _decode
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.serializers.node import FarmerExportSerializer
from v2.transactions.bulk_upload.transaction_sheet import (
    FarmerWithTransactionExcel,
)

from .constants import template_path


def get_transaction_bulk_template2(node, product, visible_fields=None):
    """To perform function get_transaction_bulk_template2."""
    visible_fields = [] if not visible_fields else visible_fields
    suppliers = node.get_suppliers(supply_chain=product.supply_chain).filter(
        type=NODE_TYPE_FARM
    )
    farmers = Farmer.objects.filter(node_ptr__in=suppliers)
    farmer_data = FarmerExportSerializer(
        farmers, many=True, context={"supply_chain": product.supply_chain}
    ).data
    for farmer in farmer_data:
        farmer["product"] = product.name
        farmer["product_id"] = product.idencode

        nsc = NodeSupplyChain.objects.filter(
            node_id=_decode(farmer["id"]), supply_chain=product.supply_chain
        )
        if nsc:
            farmer["primary_operation"] = nsc[0].primary_operation.name

    for i in range(abs(493 - len(farmer_data))):
        farmer_data.append(
            {
                "product": product.name,
                "product_id": product.idencode,
            }
        )
    data = {"farmers": farmer_data}
    excel_object = FarmerWithTransactionExcel(
        file_path=template_path, data=data, visible_columns=visible_fields
    )
    excel_object.prepare_excel()
    file = excel_object.get_excel()
    return file


def get_transaction_bulk_template(node, product, visible_fields=None):
    """To perform function get_transaction_bulk_template."""
    visible_fields = [] if not visible_fields else visible_fields
    suppliers = node.get_suppliers(supply_chain=product.supply_chain).filter(
        type=NODE_TYPE_FARM
    )
    farmers = Farmer.objects.filter(node_ptr__in=suppliers)
    farmer_data = FarmerExportSerializer(
        farmers, many=True, context={"supply_chain": product.supply_chain}
    ).data
    for farmer in farmer_data:
        farmer["product"] = product.name
        farmer["product_id"] = product.idencode

        nsc = NodeSupplyChain.objects.filter(
            node_id=_decode(farmer["id"]), supply_chain=product.supply_chain
        )
        if nsc:
            farmer["primary_operation"] = nsc[0].primary_operation.name

    for i in range(abs(493 - len(farmer_data))):
        farmer_data.append(
            {
                "product": product.name,
                "product_id": product.idencode,
            }
        )
    data = {"farmers": farmer_data}
    excel_object = FarmerWithTransactionExcel(
        file_path=template_path, data=data, visible_columns=visible_fields
    )
    excel_object.prepare_excel(product.supply_chain)
    file = excel_object.get_excel()
    return file
