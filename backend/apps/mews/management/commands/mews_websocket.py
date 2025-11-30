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
from mews.models import MewsConfiguration
from mews.websocket_client import MewsWebSocketClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run Mews WebSocket listener for real-time reservation sync"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Mews WebSocket Listener..."))

        configs = MewsConfiguration.objects.filter(is_active=True, auto_sync=True)
        if not configs.exists():
            self.stdout.write(
                self.style.ERROR("No active Mews configurations found. Please configure Mews integration first.")
            )
            return

        clients = []
        handlers = []

        for config in configs:
            try:
                self.stdout.write(self.style.SUCCESS(f"Initializing listener for tenant: {config.tenant.title}"))

                # Create event handler
                handler = ReservationEventHandler(config)
                handlers.append(handler)

                # Create WebSocket client
                client = MewsWebSocketClient(
                    client_token=config.client_token,
                    access_token=config.access_token,
                    ws_url=config.ws_url,  # pyright: ignore
                    on_event=handler.handle_event,
                    on_connected=lambda t=config.tenant.title: self._on_connected(t),
                    on_disconnected=lambda reason, t=config.tenant.title: self._on_disconnected(reason, t),
                    auto_reconnect=True,
                )

                clients.append(client)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to initialize for {config.tenant.title}: {e}"))

        if not clients:
            self.stdout.write(self.style.ERROR("No WebSocket clients initialized"))
            return

        # Setup signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING("\nShutting down Mews WebSocket listeners..."))
            for client in clients:
                try:
                    client.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting client: {e}")
            self.stdout.write(self.style.SUCCESS("Shutdown complete"))
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Connect all clients
        for client in clients:
            try:
                client.connect()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to connect client: {e}"))

        # Wait for connections
        time.sleep(2)

        # Check connection status
        connected_count = sum(1 for client in clients if client.is_connected())
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*60}\n"
                f"Mews WebSocket Listener Running\n"
                f"{'='*60}\n"
                f"Active connections: {connected_count}/{len(clients)}\n"
                f"Listening for reservation events...\n"
                f"Press Ctrl+C to stop\n"
                f"{'='*60}\n"
            )
        )

        # Keep running
        try:
            while True:
                time.sleep(1)

                # Check if any client disconnected unexpectedly
                for client in clients:
                    if not client.is_connected() and client.running:
                        logger.warning("Client disconnected unexpectedly")

        except KeyboardInterrupt:
            pass

    def _on_connected(self, tenant_name: str):
        """Callback when WebSocket connects"""
        self.stdout.write(self.style.SUCCESS(f"✓ Connected to Mews for tenant: {tenant_name}"))
        logger.info(f"WebSocket connected for {tenant_name}")

    def _on_disconnected(self, reason: str, tenant_name: str):
        """Callback when WebSocket disconnects"""
        self.stdout.write(self.style.WARNING(f"✗ Disconnected from Mews for tenant {tenant_name}: {reason}"))
        logger.warning(f"WebSocket disconnected for {tenant_name}: {reason}")
