from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Class to handle DashboardConfig and functions."""

    name = "v2.dashboard"

    def ready(self):
        """To perform function ready."""
        # method just to import the signals
        # noinspection PyUnresolvedReferences
        import v2.dashboard.signals  # noqa
