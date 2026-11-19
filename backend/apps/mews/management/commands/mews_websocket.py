"""
Django Management Command: Mews WebSocket Listener
Runs as the long-running `mews-websocket` service.
Listens for real-time reservation events from Mews and periodically re-reads the active
integrations, so enabling/disabling Mews for a tenant or changing its tokens is picked up
without a restart.
"""

import logging
import signal
import time
from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from mews.handlers import ReservationEventHandler
from mews.websocket_client import MewsWebSocketClient

from services.models import Integration
from services.utils.const import MEWS

logger = logging.getLogger(__name__)


class MewsConfigAdapter:
    def __init__(self, integration: Integration):
        additional_info = integration.additional_info or {}
        self.tenant = integration.tenant
        self.client_token = additional_info.get("client_token") or integration.integrator.client_id
        self.access_token = integration.access_token or ""
        self.company_id = integration.hotel_id or ""
        self.environment = additional_info.get("environment", "demo")

    def __repr__(self):
        return f"MewsConfigAdapter(tenant={self.tenant}, client_token={self.client_token}, access_token={self.access_token}, company_id={self.company_id}, environment={self.environment})"

    @property
    def api_base_url(self):
        """Get API base URL based on environment"""
        return {
            "demo": "https://api.mews-demo.com/api/connector/v1",
            "production": "https://api.mews.com/api/connector/v1",
        }.get(self.environment, "https://api.mews.com/api/connector/v1")

    @property
    def ws_url(self):
        """Get WebSocket URL based on environment"""
        return {
            "demo": "wss://ws.mews-demo.com/ws/connector",
            "production": "wss://ws.mews.com/ws/connector",
        }.get(self.environment, "wss://ws.mews.com/ws/connector")


RECONCILE_INTERVAL = 60


def _fingerprint(config: MewsConfigAdapter) -> tuple[str, str, str, str, str]:
    """Settings a running client depends on; any change means the client must be recreated."""
    return (
        config.client_token,
        config.access_token,
        config.ws_url,
        config.api_base_url,
        config.company_id,
    )


@dataclass
class _Listener:
    tenant_title: str
    fingerprint: tuple[str, str, str, str, str]
    client: MewsWebSocketClient


class Command(BaseCommand):
    help = "Run Mews WebSocket listener for real-time reservation sync"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown = False
        self._listeners: dict[str, _Listener] = {}

    def add_arguments(self, parser):
        parser.add_argument(
            "--reconcile-interval",
            type=int,
            default=RECONCILE_INTERVAL,
            help="Seconds between re-reading active Mews integrations (default: %(default)s)",
        )

    def handle(self, **options):
        interval = max(options["reconcile_interval"], 1)
        logger.info("Starting Mews WebSocket listener (reconcile every %ss)", interval)

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        try:
            while not self._shutdown:
                try:
                    self._reconcile()
                except Exception:
                    logger.exception("Failed to reconcile Mews listeners")

                for _ in range(interval):
                    if self._shutdown:
                        break
                    time.sleep(1)
        finally:
            self._stop_all()

    def _load_integrations(self) -> dict[str, Integration]:
        # Long-running process: drop connections PgBouncer/Postgres may have closed meanwhile
        close_old_connections()
        integrations = Integration.objects.filter(
            integrator__name__iexact=MEWS,
            integrator__client_id__isnull=False,
            enable=True,
            is_active=True,
        ).select_related("tenant", "integrator")
        return {str(integration.id): integration for integration in integrations}

    def _reconcile(self) -> None:
        """Bring running clients in line with the active integrations in the database."""
        integrations = self._load_integrations()

        for integration_id in list(self._listeners):
            if integration_id not in integrations:
                listener = self._listeners.pop(integration_id)
                logger.info("Mews integration disabled for tenant %s, stopping listener", listener.tenant_title)
                self._stop(listener)

        for integration_id, integration in integrations.items():
            config = MewsConfigAdapter(integration)
            fingerprint = _fingerprint(config)
            listener = self._listeners.get(integration_id)

            if listener is not None:
                if listener.fingerprint == fingerprint:
                    continue
                logger.info("Mews settings changed for tenant %s, restarting listener", listener.tenant_title)
                self._stop(self._listeners.pop(integration_id))

            new_listener = self._start(config, fingerprint)
            if new_listener is not None:
                self._listeners[integration_id] = new_listener

        if not self._listeners:
            logger.debug("No active Mews integrations")

    def _start(self, config: MewsConfigAdapter, fingerprint: tuple[str, str, str, str, str]) -> _Listener | None:
        tenant_title = config.tenant.title
        try:
            handler = ReservationEventHandler(config)
            client = MewsWebSocketClient(
                client_token=config.client_token,
                access_token=config.access_token,
                ws_url=config.ws_url,
                on_event=handler.handle_event,
                on_connected=lambda t=tenant_title: self._on_connected(t),
                on_disconnected=lambda reason, t=tenant_title: self._on_disconnected(reason, t),
                auto_reconnect=True,
                max_reconnect_attempts=None,
            )
            client.connect()
        except Exception:
            logger.exception("Failed to start Mews listener for tenant %s", tenant_title)
            return None

        logger.info("Started Mews listener for tenant %s", tenant_title)
        return _Listener(tenant_title=tenant_title, fingerprint=fingerprint, client=client)

    def _stop(self, listener: _Listener) -> None:
        try:
            listener.client.disconnect()
        except Exception:
            logger.exception("Error disconnecting Mews listener for tenant %s", listener.tenant_title)

    def _stop_all(self) -> None:
        if not self._listeners:
            return
        logger.info("Shutting down %s Mews listener(s)", len(self._listeners))
        for listener in self._listeners.values():
            self._stop(listener)
        self._listeners.clear()

    def _handle_signal(self, sig, frame):
        logger.info("Shutdown requested, stopping Mews listeners")
        self._shutdown = True

    def _on_connected(self, tenant_name: str):
        logger.info("Connected to Mews for tenant: %s", tenant_name)

    def _on_disconnected(self, reason: str, tenant_name: str):
        logger.warning("Disconnected from Mews for tenant %s: %s", tenant_name, reason)
