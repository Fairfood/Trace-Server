import importlib
from django.conf import settings

# Dynamically import the module based on settings.ENVIRONMENT
env = getattr(settings, 'ENVIRONMENT', 'dev')

try:
    _config = importlib.import_module(f"{__name__}.env_config.{env}")
except ModuleNotFoundError as e:
    raise ImportError(
        f"Invalid environment '{env}' for guardian.env_config"
    ) from e

#this way all upper-case settings are exposed from the env module directly.
for attr in dir(_config):
    if not attr.startswith('_'):
        globals()[attr] = getattr(_config, attr)

