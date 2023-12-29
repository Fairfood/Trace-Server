from typing import List

from celery.task import task
from common.cache import cache_proxy
from common.cache import filesystem_cache
from django.apps import apps
from django.utils import translation
from v2.products.models import Batch
from v2.products.serializers.trace_operational import (
    TraceClaimsWithBatchSerializer,
)
from v2.products.serializers.trace_operational import TraceMapSerializer
from v2.products.serializers.trace_operational import (
    TraceStagesWithBatchSerializer,
)


class ThemeCacheHandler:
    """Handler to cache, clear and rebuild Consumer Interface."""

    batch_model = apps.get_model("products", "Batch")
    theme_model = apps.get_model("dashboard", "CITheme")

    def __init__(self, proxy="filesystem", prefix="theme"):
        """Initialize proxy and prefix."""
        self.proxy = cache_proxy(proxy)
        self.prefix = prefix

    def build_keys(self, iterable: List[tuple]) -> list:
        """Build keys to handle."""
        keys = []
        for items in iterable:
            keys.append(self.prefix + "_" + "_".join(items))
        return keys

    def get_cached_keys(self, batch_id=None) -> list:
        """Returns a list of cached keys."""
        if not batch_id:
            return self.proxy.keys(self.prefix + "*")
        return self.proxy.keys(self.prefix + f"_{batch_id}*")

    def build_response(self, batch_id, theme_id, serializer_class) -> dict:
        """Build response."""
        theme = self.get_theme(theme_id)
        batch = self.get_batch(batch_id)
        serializer = serializer_class(batch, theme)
        return serializer.data

    def build_response_cache(
        self, batch_id, theme_id, lan, serializer_class, rebuild=False
    ):
        """Build new response cache."""
        key = self.build_keys([(batch_id, theme_id, lan)])[0]
        if not rebuild:
            response = self.proxy.get(key)
            if response:
                return response
        translation.activate(lan)
        response = self.build_response(batch_id, theme_id, serializer_class)
        self.proxy.set(key, response)

    def clear_response_cache(self, keys, rebuild=False):
        """Clears the response cache for the specified keys.

        Args:
        - keys: A list of cache keys to be cleared.
        - rebuild: A boolean indicating whether to rebuild the cache after
          clearing (default: False).

        Returns:
        - If rebuild is False, a string indicating that the cache keys were
          cleared.
        - If rebuild is True, a list of strings indicating the completion of
          cache rebuild for each key.
        """
        if rebuild:
            ret = []
            for key in keys:
                # Split the cache key to extract cache_id, theme_id, and lan
                key_items = key.split("_")
                cache_id, theme_id, lan = (
                    key_items[1],
                    key_items[2],
                    key_items[3],
                )

                # Rebuild cache based on prefix
                if self.prefix == "stage":
                    self.build_response_cache(
                        cache_id,
                        theme_id,
                        lan,
                        TraceStagesWithBatchSerializer,
                        rebuild=True,
                    )
                if self.prefix == "map":
                    self.build_response_cache(
                        cache_id,
                        theme_id,
                        lan,
                        TraceMapSerializer,
                        rebuild=True,
                    )
                if self.prefix == "claim":
                    self.build_response_cache(
                        cache_id,
                        theme_id,
                        lan,
                        TraceClaimsWithBatchSerializer,
                        rebuild=True,
                    )
                ret.append(f"{key} - COMPLETED")
            return ret
        else:
            self.proxy.delete_many(keys)
            return f"{keys} - CLEARED"

    def get_theme(self, theme_id) -> object:
        """Returns theme object."""
        return self.theme_model.objects.filter(pk=theme_id).last()

    def get_batch(self, batch_id) -> Batch:
        """Returns batch."""
        return self.batch_model.objects.filter(pk=batch_id).last()


def rebuild_response(instance, **kwargs):
    """Rebuilds the response by clearing the response cache for the given
    instance.

    Args:
    - instance: The instance for which the response cache should be cleared.
    - **kwargs: Additional keyword arguments to be passed to the
      `clear_response_cache` method.

    Returns:
    - The result of clearing the response cache.
    """
    return instance.clear_response_cache(**kwargs)


def clear_ci_cache(batch_id, prefix, ignore_parents=False):
    """Task to clear CI theme batches and related batches.

    Args:
        batch_id: Batch.id
        prefix: map/stage
    """
    handler = ThemeCacheHandler(prefix=prefix)
    batch = handler.get_batch(batch_id)

    if not batch:
        return "NO BATCH FOUND"
    if not batch.source_transaction:
        return "NO SOURCE  TRANSACTION FOUND"

    if not ignore_parents:
        # Getting all related transaction to the source transaction.
        related_transaction_ids = list(
            batch.source_transaction.get_parent_transactions().values_list(  # noqa
                "id", flat=True
            )
        )

        batches = handler.batch_model.objects.filter(
            source_transaction__in=related_transaction_ids
        ).values_list("id", flat=True)
        keys = []
        for batch_id in batches:
            keys.extend(handler.get_cached_keys(batch_id))
    else:
        keys = handler.get_cached_keys(batch_id)
    if not keys:
        return "NO CACHE TO REBUILT"
    return rebuild_response(handler, keys=keys, rebuild=True)


def get_batches(instance_id: int) -> List[str]:
    """Getting batch ids from cached keys.

    Assuming we are using filesystem caching.
    """
    # Need to change cache if cache backend changes.
    cache = filesystem_cache
    keys = cache.keys(f"*_{instance_id}_*")
    return [key.split("_")[1] for key in keys]


# def terminate_active_tasks(batch_id: int, task_name: str) -> None:
#     # """
#     # If the rebuild happening again simultaneously, them previous tasks
#     # will be killed.
#     # """
#     #
#     # # fetch active tasks
#     # inspect = app.control.inspect()
#     # active_workers = inspect.active()
#     #
#     # # Terminate already running tasks.
#     # for _, worker in active_workers.items():
#     #     for _task in worker:
#     #         if (_task['name'] == task_name
#     #                 and _task['args'] == [batch_id]):
#     #             app.control.revoke(_task['id'], terminate=True)
#     pass


@task(name="clear-ci-stage-cache", queue="ci_queue")
def clear_ci_stage_cache(batch_id, ignore_parents=False):
    """Task to clear the CI stage cache for a specific batch.

    Args:
    - batch_id: The ID of the batch for which the CI stage cache should be
      cleared.

    Returns:
    - The result of clearing the CI stage cache.
    """
    return clear_ci_cache(batch_id, "stage", ignore_parents=ignore_parents)


@task(name="clear-ci-map-cache", queue="ci_queue")
def clear_ci_map_cache(batch_id, ignore_parents=False):
    """Task to clear the CI map cache for a specific batch.

    Args:
    - batch_id: The ID of the batch for which the CI map cache should be
      cleared.

    Returns:
    - The result of clearing the CI map cache.
    """
    return clear_ci_cache(batch_id, "map", ignore_parents=ignore_parents)


@task(name="clear-ci-claim-cache", queue="ci_queue")
def clear_ci_claim_cache(batch_id, ignore_parents=False):
    """Task to clear the CI claim cache for a specific batch.

    Args:
    - batch_id: The ID of the batch for which the CI claim cache should be
      cleared.

    Returns:
    - The result of clearing the CI claim cache.
    """
    return clear_ci_cache(batch_id, "claim", ignore_parents=ignore_parents)
