"""
Mews WebSocket Client for Real-Time Reservation Events
Connects to Mews WebSocket API and listens for reservation changes
"""

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    # Try websocket-client package first (provides WebSocketApp)
    from websocket import WebSocketApp
except ImportError:
    # Fallback: simple-websocket doesn't have WebSocketApp
    # Need to install websocket-client
    raise ImportError("websocket-client package is required. Install with: pip install websocket-client")

logger = logging.getLogger(__name__)


class MewsWebSocketClient:
    """WebSocket client for receiving real-time Mews reservation events"""

    def __init__(
        self,
        client_token: str,
        access_token: str,
        ws_url: str,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[str], None]] = None,
        auto_reconnect: bool = True,
        ping_interval: int = 300,  # 5 minutes
        max_reconnect_attempts: Optional[int] = None,
    ):
        """
        Initialize Mews WebSocket Client

        Args:
            client_token: Mews ClientToken
            access_token: Mews AccessToken
            ws_url: WebSocket URL (from MewsConfiguration.ws_url)
            on_event: Callback when reservation event received
            on_connected: Callback when connection established
            on_disconnected: Callback when connection lost
            auto_reconnect: Auto-reconnect on disconnect
            ping_interval: Seconds between pings
            max_reconnect_attempts: Max reconnect attempts before giving up (None = unlimited)
        """
        self.client_token = client_token
        self.access_token = access_token
        self.ws_url = ws_url
        self.on_event = on_event
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.auto_reconnect = auto_reconnect
        self.ping_interval = ping_interval
        self.max_reconnect_attempts = max_reconnect_attempts

        # Connection state
        self.ws = None
        self.connected = False
        self.running = False
        self.reconnect_count = 0
        self.last_pong_time = None
        self.connection_start_time = None

        # Threading
        self.connection_thread = None
        self.ping_thread = None

    def _get_cookie_header(self) -> str:
        """
        Generate cookie header for WebSocket authentication
        CRITICAL: No spaces around '=' signs
        """
        return f"ClientToken={self.client_token}; AccessToken={self.access_token}"

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            logger.debug(f"Received message: {data}")

            # Process events
            events = data.get("Events", [])
            for event in events:
                if event.get("Type") == "Reservation":
                    if self.on_event:
                        try:
                            self.on_event(event)
                        except Exception as e:
                            logger.error(f"Error in event handler: {e}", exc_info=True)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        self.connected = False
        logger.debug(f"WebSocket closed. Code: {close_status_code}, Message: {close_msg}")

        if close_status_code == 1008:
            logger.error("Unauthorized - check your Mews tokens")
        elif close_status_code == 1013:
            logger.warning("Rate limiting - will retry later")

        # Reset backoff only if connection was stable (>= 30s)
        connection_duration = time.time() - (self.connection_start_time or 0)
        if connection_duration >= 30:
            self.reconnect_count = 0

        # Notify user
        if self.on_disconnected:
            try:
                self.on_disconnected(close_msg or "Connection closed")
            except Exception as e:
                logger.error(f"Error in disconnected callback: {e}", exc_info=True)

        # Auto-reconnect if enabled
        if self.auto_reconnect and self.running:
            self._schedule_reconnect()

    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        self.connected = True
        self.connection_start_time = time.time()
        self.last_pong_time = self.connection_start_time
        logger.debug("WebSocket connection established")

        # Notify user
        if self.on_connected:
            try:
                self.on_connected()
            except Exception as e:
                logger.error(f"Error in connected callback: {e}", exc_info=True)

        # Start ping thread
        self._start_ping_thread()

    def _on_pong(self, ws, message):
        """Handle pong response"""
        self.last_pong_time = time.time()
        logger.debug("Received pong")

    def _start_ping_thread(self):
        """Start thread to send periodic pings"""
        if self.ping_thread and self.ping_thread.is_alive():
            return

        def ping_worker():
            while self.connected and self.running:
                try:
                    time.sleep(self.ping_interval)

                    if not self.connected or not self.running:
                        break

                    # Send ping via the underlying socket
                    logger.debug("Sending ping")
                    if self.ws and self.ws.sock:
                        self.ws.sock.ping()
                    else:
                        logger.warning("WebSocket not ready for ping")
                        break

                    # Check for pong
                    time.sleep(5)
                    if self.last_pong_time:
                        time_since_pong = time.time() - self.last_pong_time
                        if time_since_pong > 60:  # 60s timeout
                            logger.warning(f"No pong for {time_since_pong:.1f}s. Reconnecting...")
                            self.ws.close()
                            break

                except Exception as e:
                    logger.error(f"Error in ping thread: {e}", exc_info=True)
                    break

        self.ping_thread = threading.Thread(target=ping_worker, daemon=True)
        self.ping_thread.start()

    def _schedule_reconnect(self):
        """Schedule reconnection with exponential backoff in a separate thread"""
        if self.max_reconnect_attempts is not None and self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached. Giving up.")
            self.running = False
            return

        # Backoff: 5s, 10s, 20s, 40s, 60s, 120s (max)
        delay = min(5 * (2**self.reconnect_count), 120)
        self.reconnect_count += 1

        attempts_info = (
            f"{self.reconnect_count}/{self.max_reconnect_attempts}"
            if self.max_reconnect_attempts is not None
            else str(self.reconnect_count)
        )
        logger.info(f"Reconnecting in {delay}s (attempt {attempts_info})...")

        def _reconnect_worker():
            time.sleep(delay)
            if self.running:
                self.connect()

        threading.Thread(target=_reconnect_worker, daemon=True).start()

    def connect(self):
        """Connect to Mews WebSocket server"""
        if self.connected:
            logger.warning("Already connected")
            return

        try:
            logger.debug(f"Connecting to {self.ws_url}...")

            # Create WebSocket connection
            self.ws = WebSocketApp(
                self.ws_url,
                cookie=self._get_cookie_header(),
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open,
                on_pong=self._on_pong,
            )

            self.running = True

            # Run in separate thread
            self.connection_thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={
                    "ping_interval": 0,  # We handle pings manually
                    "ping_timeout": None,
                },
                daemon=True,
            )
            self.connection_thread.start()

        except Exception as e:
            logger.error(f"Failed to connect: {e}", exc_info=True)
            if self.auto_reconnect and self.running:
                self._schedule_reconnect()

    def disconnect(self):
        """Gracefully disconnect"""
        logger.info("Disconnecting from Mews WebSocket...")
        self.running = False
        self.auto_reconnect = False

        if self.ws:
            self.ws.close()

        # Wait for threads
        if self.connection_thread and self.connection_thread.is_alive():
            self.connection_thread.join(timeout=5)

        if self.ping_thread and self.ping_thread.is_alive():
            self.ping_thread.join(timeout=5)

        self.connected = False
        logger.info("Disconnected successfully")

    def wait_for_connection(self, timeout: int = 10) -> bool:
        """
        Wait for connection to be established

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if connected, False if timeout
        """
        start_time = time.time()
        while not self.connected and time.time() - start_time < timeout:
            time.sleep(0.1)

        return self.connected

    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self.connected
