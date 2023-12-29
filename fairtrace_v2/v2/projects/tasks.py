from celery.task import task
from django.apps import apps    
from . import synch

@task(name="trace_sync", queue="low")
def final_sync(node_id, projct_owner_id):
    """Celery task to sync fanal data."""
    NodeModel = apps.get_model("supply_chains", "Node")
    node = NodeModel.objects.get(id=node_id)
    synch.start(node)
    if node_id != projct_owner_id:
        project_owner = NodeModel.objects.get(id=projct_owner_id)
        synch.start(project_owner)
    return "Syncing started"
