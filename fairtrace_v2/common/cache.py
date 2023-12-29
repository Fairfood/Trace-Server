import re

from django.core.cache.backends.filebased import FileBasedCache
from django.utils import timezone
from django.utils.cache import caches


class FileBasedCacheOperational(FileBasedCache):
    """Class to handle FileBasedCacheOperational and functions."""

    def keys(self, search: str):
        """To perform function keys."""
        key_list = self.get("keys", default=[])
        if "*" in search:
            search = search.replace("*", ".*")
        search_re = re.compile(search)
        if not key_list:
            return []
        return list(filter(search_re.fullmatch, key_list))

    def set(self, key, value, **kwargs):
        """To perform function set."""
        super().set(key, value, **kwargs)
        key_list = self.keys("*")
        if key not in key_list:
            key_list.append(key)
            super().set("keys", key_list)

    def delete(self, key, **kwargs):
        """To perform function lete."""
        super().delete(key, **kwargs)
        key_list = self.keys("*")
        if key in key_list:
            key_list.remove(key)
            super().set("keys", key_list)


class CacheProxy:
    """Proxy access to the multiple type Cache object's attributes.

    This allows the legacy `cache` object to be thread-safe using the new
    ``caches`` API.

    Why using a proxy.
    It will make caching thread-safe while multiple API calls.
    It will be easier to handle a Proxy object and switch between cache
    backends.

    eg:
        cache_proxy = CacheProxy('filesystem')
    """

    def __init__(self, alias="default"):
        """To perform function __init__."""
        # Directly assigning to instance may invoke __setattr__
        # and __getattr__ methods.
        self.__dict__["alias"] = alias

    def __getattr__(self, name):
        """To perform function __getattr__."""
        return getattr(caches[self.alias], name)

    def __setattr__(self, name, value):
        """To perform function __setattr__."""
        return setattr(caches[self.alias], name, value)

    def __delattr__(self, name):
        """To perform function __delattr__."""
        return delattr(caches[self.alias], name)

    def __contains__(self, key):
        """To perform function __contains__."""
        return key in caches[self.alias]

    def __eq__(self, other):
        """To perform function __eq__."""
        return caches[self.alias] == other


cache_proxy = CacheProxy

cache = cache_proxy()

filesystem_cache = cache_proxy("filesystem")


class MetaCacheHandler:
    """Class to handle MetaCacheHandler and functions."""

    def __init__(self, cache):
        """To perform function __init__."""
        self.cache = cache
        self._metadata = self.cache.get("metadata", {})
        self._key = None

    def _close_metadata(self):
        """To perform function _close_metadata."""
        self.cache.set("metadata", self._metadata)

    def get_metadata(self):
        """To perform function get_metadata."""
        return self._metadata.get(self._key, None)

    def set_metadata(self, key):
        """To perform function set_metadata."""
        self._key = key
        if self.get_metadata():
            self._update_metadata(key)
        else:
            self._metadata[key] = {
                "created_on": timezone.now(),
                "rebuild": 0,
                "updated_on": timezone.now(),
            }
        self._close_metadata()

    def _update_metadata(self, key):
        """To perform function _update_metadata."""
        self._metadata[key]["updated_on"] = timezone.now()
        self._metadata[key]["rebuild"] += 1

    metadata = property(fget=get_metadata, fset=set_metadata)
