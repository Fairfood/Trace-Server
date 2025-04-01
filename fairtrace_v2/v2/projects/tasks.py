from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django.apps import apps  
from django.core.cache import cache
from sentry_sdk import capture_exception, capture_message 
from common.library import _decode
from . import synch
from v2.projects.reverse_sync import ReverseSync
from .navigate import NavigateAPI
from . import constants
from v2.projects.connect import ConnectAPI
from v2.projects.models import Synchronization
from v2.projects import constants as proj_consts
from v2.supply_chains.models.node import Node
from v2.supply_chains.models.profile import Farmer, Company


@shared_task(name="trace_sync", queue="low")
def final_sync(node_id, projct_owner_id):
    """Celery task to sync fanal data."""
    NodeModel = apps.get_model("supply_chains", "Node")
    node = NodeModel.objects.get(id=node_id)
    synch.start(node)
    if node_id != projct_owner_id:
        project_owner = NodeModel.objects.get(id=projct_owner_id)
        synch.start(project_owner)
    return "Syncing started"

@shared_task(name="sync_from_connect")
def sync_from_connect(node_id: str, sync_id: str):
    """Function to start sync."""
    ReverseSync(node_id, sync_id).start_sync()
    return "Sync from connect completed"

@shared_task(name="daily_sync_from_connect")
def daily_sync_from_connect():
    """Function to start sync."""
    nodes = Node.objects.filter(features__link_connect=True)
    existing_syncs = Synchronization.objects.filter(
        node__in=nodes,
        sync_type=proj_consts.SYNC_TYPE_CONNCET,
        status=proj_consts.SYNC_STATUS_IN_PROGRESS
    ).values_list('node_id', flat=True)
    nodes_to_sync = nodes.exclude(id__in=existing_syncs)
    
    for node in nodes_to_sync:
        sync = Synchronization.objects.create(
            node=node,
            sync_type=proj_consts.SYNC_TYPE_CONNCET
        )
        reverese_sync = ReverseSync(
            node_id=node.idencode, sync_id=sync.idencode
        )
        reverese_sync.start_sync()
    return "Sync from connect completed"
    
@shared_task(name="sync_to_navigate", queue="high")
def sync_to_navigate(node_id, sync_id, supply_chain_id=None):
    """
    Function to start sync.

    Args:
        node_id (int): The ID of the node.
        supply_chain_id (int, optional): The ID of the supply chain. 
        Defaults to None.

    Returns:
        str: A message indicating the completion of syncing.

    Raises:
        Exception: If an error occurs during syncing.
    """
    # Retrieve the Node and Sync models
    NodeModel = apps.get_model("supply_chains", "Node")

    # Get the node object based on the provided node_id
    node = NodeModel.objects.get(id=node_id)

    # If supply_chain_id is provided, get the corresponding supply chain object
    supply_chain = None
    if supply_chain_id:
        supply_chain = node.company.supply_chains.filter(
            id=supply_chain_id).last()

    try:
        # Perform the syncing using the NavigateAPI
        navigate = NavigateAPI(sync_id)
        navigate.update_company(node.company)
        for member in node.company.nodemembers.all():
            navigate.create_company_member(member, node.company)
        navigate.create_company_supply_chains(node.company)
        navigate.create_company_farmers(node.company)
        navigate.create_company_batches(node.company, supply_chain)
        navigate._update_sync_status(node.company)
    except Exception as e:
        capture_exception(e)

    return "Syncing completed"


@shared_task(name="add_or_update_farmer_to_connect")
def add_or_update_farmer_to_connect(famer_id):
    """Add or update farmer from trace to connect"""
    try:
        farmer = Farmer.objects.get(id=_decode(famer_id))
        company = farmer.invitations_received.first().inviter
        connect = ConnectAPI()
        if farmer.external_id:
            connect.update_farmer(farmer, company)
        else:
            if external_id := connect.add_farmer(farmer, company):
                Farmer.objects.filter(
                    id=_decode(famer_id)
                ).update(external_id=external_id)
    except Exception as e:
        capture_exception(e)
    cache.delete(f"farmer_connect_sync_{farmer.idencode}")
    return "Synced To Connect Successfully"


@shared_task(name="delete_old_synchronizations")
def delete_old_synchronizations():
    """Delete old synchronizations"""
    now = timezone.now()
    three_months_ago = now - timedelta(days=90)
    Synchronization.objects.filter(created_on__lt=three_months_ago).delete()
    return "Sync deleted successfully"