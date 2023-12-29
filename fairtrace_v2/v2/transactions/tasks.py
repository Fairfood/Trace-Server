"""Celery tasks from Supply chain app."""
from celery.decorators import task
from scripts.app_transactions import export_txn
from v2.transactions.models import Transaction


@task(name="transaction_follow_up", queue="low")
def transaction_follow_up(transaction_id):
    """Follow-up tasks after a transaction."""
    transaction = Transaction.objects.get(id=transaction_id)
    child = transaction.transaction_object
    child.log_activity()
    child.notify()
    child.log_blockchain_transaction()
    child.update_cache()
    return True


@task(name="export_app_txn", queue="low")
def export_app_txn() -> bool:
    """Export_app_txn.

    :return: bool
    """
    export_txn()
    return True
