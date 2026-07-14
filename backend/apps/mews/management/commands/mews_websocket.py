"""
Django Management Command: Mews WebSocket Listener
Runs as a long-running process managed by supervisord
Listens for real-time reservation events from Mews
"""

import logging
import signal
import sys
import time

from django.core.management.base import BaseCommand
from mews.handlers import ReservationEventHandler
from mews.websocket_client import MewsWebSocketClient

from services.models import Integration
from services.utils.const import MEWS

logger = logging.getLogger(__name__)


class MewsConfigAdapter:
    def __init__(self, integration: Integration):
        additional_info = integration.additional_info or {}
        self.tenant = integration.tenant
        self.client_token = integration.integrator.client_id
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


RETRY_INTERVAL = 60


class Command(BaseCommand):
    help = "Run Mews WebSocket listener for real-time reservation sync"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown = False

    def handle(self, **_):
        self.stdout.write(self.style.SUCCESS("Starting Mews WebSocket Listener..."))

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        active_integrations = self._wait_for_config()
        if active_integrations is None:
            return

        clients = []
        handlers = []

        for integration in active_integrations:
            tenant = integration.tenant
            try:
                self.stdout.write(self.style.SUCCESS(f"Initializing listener for tenant: {tenant.title}"))

                config_adapter = MewsConfigAdapter(integration)

                handler = ReservationEventHandler(config_adapter)
                handlers.append(handler)

                client = MewsWebSocketClient(
                    client_token=config_adapter.client_token,
                    access_token=config_adapter.access_token,
                    ws_url=config_adapter.ws_url,
                    on_event=handler.handle_event,
                    on_connected=lambda t=tenant.title: self._on_connected(t),
                    on_disconnected=lambda reason, t=tenant.title: self._on_disconnected(reason, t),
                    auto_reconnect=True,
                    max_reconnect_attempts=5,
                )

                clients.append(client)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to initialize for {tenant.title}: {e}"))

        if not clients:
            self.stdout.write(self.style.ERROR("No WebSocket clients initialized"))
            return

        # Override signal handlers to disconnect clients on shutdown
        def shutdown_handler(sig, frame):
            self.stdout.write(self.style.WARNING("\nShutting down Mews WebSocket listeners..."))
            for client in clients:
                try:
                    client.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting client: {e}")
            self.stdout.write(self.style.SUCCESS("Shutdown complete"))
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        for client in clients:
            try:
                client.connect()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to connect client: {e}"))

        time.sleep(2)

        connected_count = sum(1 for client in clients if client.is_connected())
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'=' * 60}\n"
                f"Mews WebSocket Listener Running\n"
                f"{'=' * 60}\n"
                f"Active connections: {connected_count}/{len(clients)}\n"
                f"Listening for reservation events...\n"
                f"Press Ctrl+C to stop\n"
                f"{'=' * 60}\n"
            )
        )

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def _wait_for_config(self):
        """Poll until active Mews integrations appear. Returns queryset or None on shutdown."""
        while not self._shutdown:
            integrations = list(
                Integration.objects.filter(
                    integrator__name__iexact=MEWS,
                    integrator__client_id__isnull=False,
                    enable=True,
                    is_active=True,
                ).select_related("tenant")
            )
            if integrations:
                return integrations

            self.stdout.write(
                self.style.WARNING(f"No active Mews configurations found. Retrying in {RETRY_INTERVAL}s...")
            )
            for _ in range(RETRY_INTERVAL):
                if self._shutdown:
                    return None
                time.sleep(1)

        return None

    def _handle_signal(self, sig, frame):
        self.stdout.write(self.style.WARNING("Shutdown requested, stopping..."))
        self._shutdown = True

    def _on_connected(self, tenant_name: str):
        self.stdout.write(self.style.SUCCESS(f"✓ Connected to Mews for tenant: {tenant_name}"))
        logger.info(f"Connected to Mews for tenant: {tenant_name}")

    def _on_disconnected(self, reason: str, tenant_name: str):
        self.stdout.write(self.style.WARNING(f"✗ Disconnected from Mews for tenant {tenant_name}: {reason}"))
        logger.warning(f"Disconnected from Mews for tenant {tenant_name}: {reason}")
