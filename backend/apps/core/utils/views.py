from typing import cast

from django.core.cache import caches

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import DestroyModelMixin, UpdateModelMixin

from core.utils.cache import QUICK_CACHE_PREFIX


class UpdateDestroyAPIView(UpdateModelMixin, DestroyModelMixin, GenericAPIView):
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


CACHE_TTL = 60 * 5


class TenantCachedMixin:
    cache_key_prefix: str
    cache_ttl: int = CACHE_TTL
    cache_name: str = "http"

    def _build_cache_key(self, tenant_id: str, **kwargs) -> str:
        base = f"{QUICK_CACHE_PREFIX}:{self.cache_key_prefix}:{tenant_id}"
        params = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
        return f"{base}:{params}" if params else base

    def get_cached_data(self, tenant_id: str, **kwargs) -> list:
        cache = caches[self.cache_name]
        cache_key = self._build_cache_key(tenant_id, **kwargs)
        return cast(list, cache.get_or_set(cache_key, lambda: self.get_data(tenant_id, **kwargs), self.cache_ttl))

    def get_data(self, tenant_id: str, **kwargs) -> list:
        raise NotImplementedError
