from openpyxl import load_workbook
from openpyxl.writer.excel import save_virtual_workbook
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Farmer
from v2.supply_chains.serializers.node import FarmerExportSerializer

from .constants import farmer_excel_path
from .farmer_sheet import FarmerExcel


def get_farmer_bulk_template():
    """To perform function get_farmer_bulk_template."""
    workbook = load_workbook(farmer_excel_path)
    data = save_virtual_workbook(workbook)
    return data


def export_farmers(node, supply_chain, visible_fields=None):
    """To perform function xport_farmers."""
    visible_fields = [] if not visible_fields else visible_fields
    suppliers = node.get_suppliers(supply_chain=supply_chain).filter(
        type=NODE_TYPE_FARM
    )
    farmers = Farmer.objects.filter(node_ptr__in=suppliers)
    farmer_data = FarmerExportSerializer(
        farmers, many=True, context={"supply_chain": supply_chain}
    ).data
    data = {"farmers": farmer_data}
    excel_object = FarmerExcel(
        file_path=farmer_excel_path, data=data, visible_columns=visible_fields
    )
    excel_object.prepare_excel(supply_chain)
    file = excel_object.get_excel()
    return file
