import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async

from services.models import Integration
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer

logger = logging.getLogger(__name__)


@database_sync_to_async
def resolve_integration(scope):
    """Resolve the ``Integration`` (and thus the tenant) for a services websocket
    connection from the same credentials ``DoorLockPermission`` expects on REST:
    a ``ClientToken`` / ``AccessToken`` pair. Both are accepted either as headers
    or as query-string params (browsers cannot set custom websocket headers).
    Returns ``None`` when the credentials are missing or do not match."""
    headers = {key.decode().lower(): value.decode() for key, value in scope.get("headers", [])}
    query = parse_qs(scope.get("query_string", b"").decode())

    client_token = headers.get("clienttoken") or query.get("client_token", [None])[0]
    access_token = headers.get("accesstoken") or query.get("access_token", [None])[0]
    if not client_token or not access_token:
        return None

    try:
        return Integration.objects.select_related("tenant").get(
            access_token=access_token, integrator__client_id=client_token, is_active=True, enable=True
        )
    except Integration.DoesNotExist:
        return None
    except Integration.MultipleObjectsReturned:
        logger.error("Integration AccessToken is not unique.")
        return None


class TenantScopedConsumer(BaseGenericAsyncAPIConsumer):
    """Base for services websocket consumers. The tenant is resolved once by the
    demultiplexer (``resolve_integration``) and injected into the shared scope,
    mirroring ``DoorLockPermission`` used by the REST endpoints. Unlike the shuttle
    v2 consumers there is no JWT user in scope, so ``tenant`` / ``tenant_id`` read
    from the resolved integration instead of ``scope["user"]``."""

    @property
    def integration(self):
        return self.scope.get("integration")

    @property
    def tenant(self):
        return self.scope.get("tenant")

    @property
    def tenant_id(self):
        return getattr(self.tenant, "id", None)
