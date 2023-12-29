from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    """Class to handle TransactionsConfig and functions."""

    name = "transactions"

    def ready(self):  # method just to import the signals
        """To perform function ready."""
        # noinspection PyUnresolvedReferences
        from v2.transactions import signals  # noqa
