import tqdm
from django.apps import apps


def update_payment_roles():
    """To update roles in existing payments."""
    payment_model = apps.get_model("projects", "Payment")
    payments = payment_model.objects.all()
    update_set = []
    for payment in tqdm.tqdm(payments):
        # noinspection PyProtectedMember
        payment._update_from_transaction()
        # noinspection PyProtectedMember
        payment._update_payment_status()
        # noinspection PyProtectedMember
        payment._update_verification_method()
        update_set.append(payment)

    # updating batch wise.
    batch_size = 100
    payment_model.objects.bulk_update(
        update_set,
        [
            "source",
            "destination",
            "payment_type",
            "invoice",
            "currency",
            "verification_latitude",
            "verification_longitude",
            "method",
            "created_on",
            "updated_on",
            "creator",
            "updater",
        ],
        batch_size,
    )
    print("Done")


def update_base_transaction_entry():
    """To update base transaction entry."""
    transaction_model = apps.get_model("transactions", "ExternalTransaction")
    transactions = transaction_model.objects.all()

    for transaction in tqdm.tqdm(transactions):
        transaction.update_payments()
    print("Done")


def update_premium_owners():
    """Update premium owners.

    This function updates the owners of premium objects in the "projects" app.
    It retrieves all the premium objects from the database and iterates over
    them, calling the private method `_update_owner()` on each premium object.
    The updated premium objects are added to an update set.

    Once all the premium objects have been processed, the function updates the
    "owner" field of the premium objects in the update set using a bulk update
    operation with a specified batch size. Finally, it prints "Done" to
    indicate the completion of the update process.
    """
    premium_model = apps.get_model("projects", "ProjectPremium")
    premiums = premium_model.objects.all()
    update_set = []
    for premium in premiums:
        # noinspection PyProtectedMember
        premium._update_owner()
        update_set.append(premium)

    # updating batch wise.
    batch_size = 100
    premium_model.objects.bulk_update(update_set, ["owner"], batch_size)
    print("Done")


def run():
    """Executes a series of update tasks.

    This function is responsible for executing a series of update tasks
    in a specific order. The tasks include updating payment roles,
    updating base transaction entries, and updating premium owners.

    Note:
    The execution of each task is dependent on the successful execution
    of the previous task. If any task encounters an error, the function
    will terminate without executing subsequent tasks.

    Raises:
    - Exception: If any of the update tasks encounter an error.
    """
    update_payment_roles()
    update_base_transaction_entry()
    update_premium_owners()
