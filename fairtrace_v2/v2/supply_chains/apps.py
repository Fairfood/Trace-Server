from django.apps import AppConfig


class SupplyChainsConfig(AppConfig):
    """Class to handle SupplyChainsConfig and functions."""

    name = "v2.supply_chains"

    def ready(self):  # method just to import the signals
        """To perform function ready."""
        pass
