from celery import shared_task
from common.library import _generate_random_number

from .copy_node_connections import copy_buyer_connections
from .copy_node_connections import copy_company
from .copy_node_connections import copy_node_member
from .copy_node_connections import copy_other_datas
from .copy_node_connections import copy_supplier_connections


@shared_task(name="copy_connctions", queue="low")
def copy_connctions(node_id, source_sc_id, target_sc_id):
    """To perform function copy_connctions."""
    print("node_id------------------------------", node_id)
    print("source_sc_id_____________________", source_sc_id)
    print("target_sc_id_____________________", target_sc_id)
    name = " copy_" + str(_generate_random_number(4))
    company_new = copy_company(node_id, name)
    copy_other_datas(
        node_id, company_new, target_sc_id, name, source_sc_id, conn_node=None
    )
    copy_node_member(node_id, company_new)
    copy_supplier_connections(
        node_id, company_new, source_sc_id, name, target_sc_id
    )
    copy_buyer_connections(
        node_id, company_new, source_sc_id, name, target_sc_id
    )
    return True
