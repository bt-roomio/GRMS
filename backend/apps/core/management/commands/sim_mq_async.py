"""Generate fake messages for the async RabbitMQ consumer (``mq_async``).

Every shape routed by :mod:`core.management.mq.engine.processor` (by ``topic``)
can be produced here: telemetry, attributes, gateway connect/disconnect,
shared-attribute requests and RPC confirmations. Message templates mirror
``backend/docs/rabbitmq/queues.md``.

Because the consumer resolves the source device by ``sourceDeviceUUID`` before
doing anything else (unknown devices are dropped, not requeued), messages are
built from **real** devices in the database. Devices that have a parent gateway
relation are emitted in the gateway shape (``sourceDeviceUUID`` = gateway,
sub-device addressed by name); standalone devices use the direct shape.

Examples::

    # one telemetry message per device
    ./manage.py sim_mq_async

    # 500 attribute messages for a single tenant, 50ms apart
    ./manage.py sim_mq_async --type attributes --tenant <uuid> --count 500 --interval 0.05

    # print without publishing
    ./manage.py sim_mq_async --type rfid --dry-run
"""

import itertools
import random
import time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.get_time import get_mil_sec
from main.models import Device
from shuttle.models import Relation

# Telemetry keys and the range of plausible values each one takes.
TELEMETRY_KEYS = {
    "MUR Relay": (0, 1),
    "AC ON OFF": (0, 1),
    "Occupancy State": (0, 1),
    "Room Temperature": (16, 30),
    "Wifi Relay": (0, 1),
}

# Shared-attribute keys used for attribute messages/requests.
ATTRIBUTE_KEYS = ["dnd", "mur", "someSharedKey"]

# type -> queue (routing key) the message is published to. Routing inside the
# consumer is by ``topic``, so any queue in QUEUE_CONFIG works; each type is sent
# to the queue it naturally arrives on in production.
QUEUE_BY_TYPE = {
    "telemetry": "/telemetry",
    "rfid": "/telemetry",
    "attributes": "/attributes",
    "connect": "/attributes",
    "disconnect": "/attributes",
    "attr-request": "v1/devices/me/attributes/request",
    "rpc": "v1/gateway/rpc",
}


class DeviceCtx:
    """A device plus the parent gateway it hangs off of (if any)."""

    __slots__ = ("gateway_id", "name", "own_id")

    def __init__(self, own_id: str, name: str, gateway_id: str | None):
        self.own_id = own_id
        self.name = name
        # Devices with a parent relation are addressed through the gateway;
        # standalone devices act as their own source.
        self.gateway_id = gateway_id or own_id

    @property
    def is_sub_device(self) -> bool:
        return self.gateway_id != self.own_id


class Command(BaseCommand):
    help = "Generate fake messages for the mq_async consumer and publish them to RabbitMQ."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=sorted(QUEUE_BY_TYPE),
            default="telemetry",
            help="Message shape to generate (default: telemetry).",
        )
        parser.add_argument("--tenant", help="Only use devices of this tenant id.")
        parser.add_argument("--device", help="Only use this single device id.")
        parser.add_argument(
            "--count",
            type=int,
            help="Total number of messages to publish (cycles through devices). Default: one per device.",
        )
        parser.add_argument("--limit", type=int, help="Cap the number of devices used.")
        parser.add_argument(
            "--interval",
            type=float,
            default=0.0,
            help="Seconds to sleep between publishes (default: 0).",
        )
        parser.add_argument(
            "--queue",
            help="Override the queue/routing key (e.g. toGRMS to route through the catch-all).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print messages instead of publishing them.",
        )

    def handle(self, *, type, tenant, device, count, limit, interval, queue, dry_run, **_):
        contexts = self._device_contexts(tenant_id=tenant, device_id=device, limit=limit)
        if not contexts:
            raise CommandError("No matching devices found — cannot build messages.")

        routing_key = queue or QUEUE_BY_TYPE[type]
        builder = self._builder_for(type)

        channel = None if dry_run else connect_to_rabbitmq()
        total = count if count else len(contexts)

        sent = 0
        for ctx in itertools.islice(itertools.cycle(contexts), total):
            msg = builder(ctx)
            if dry_run:
                self.stdout.write(str(msg))
            else:
                assert channel is not None
                send_to_rabbitmq(channel, msg, routing_key)
            sent += 1
            if interval and sent < total:
                time.sleep(interval)

        verb = "Would publish" if dry_run else "Published"
        self.stdout.write(self.style.SUCCESS(f"{verb} {sent} '{type}' message(s) to '{routing_key}'."))

    # -- device selection ---------------------------------------------------

    def _device_contexts(self, *, tenant_id=None, device_id=None, limit=None) -> list[DeviceCtx]:
        """Load devices with their parent gateway relation prefetched."""
        devices = Device.objects.prefetch_related(
            Prefetch(
                "to_relations",
                queryset=Relation.objects.select_related("from_id"),
                to_attr="parents",
            )
        )
        if device_id:
            devices = devices.filter(id=device_id)
        if tenant_id:
            devices = devices.filter(tenant_id=tenant_id)
        if limit:
            devices = devices[:limit]

        contexts = []
        for d in devices:
            parents = getattr(d, "parents", [])
            gateway_id = str(parents[0].from_id_id) if parents else None
            contexts.append(DeviceCtx(str(d.id), d.name, gateway_id))
        return contexts

    # -- builder dispatch ---------------------------------------------------

    def _builder_for(self, msg_type: str):
        return {
            "telemetry": self.build_telemetry,
            "rfid": self.build_rfid,
            "attributes": self.build_attributes,
            "connect": lambda ctx: self.build_device_activity(ctx, connected=True),
            "disconnect": lambda ctx: self.build_device_activity(ctx, connected=False),
            "attr-request": self.build_attribute_request,
            "rpc": self.build_rpc,
        }[msg_type]

    # -- message builders ---------------------------------------------------

    @staticmethod
    def _telemetry_values() -> dict:
        return {key: random.randint(low, high) for key, (low, high) in TELEMETRY_KEYS.items()}

    def build_telemetry(self, ctx: DeviceCtx) -> dict:
        entry = {"ts": get_mil_sec(), "values": self._telemetry_values()}
        if ctx.is_sub_device:
            return {
                "sourceDeviceUUID": ctx.gateway_id,
                "topic": "v1/gateway/telemetry",
                "data": {ctx.name: [entry]},
            }
        # Standalone device: topic ends with /telemetry, data is a bare list.
        return {
            "sourceDeviceUUID": ctx.own_id,
            "topic": "v1/devices/me/telemetry",
            "data": [entry],
        }

    def build_rfid(self, ctx: DeviceCtx) -> dict:
        event_ts = get_mil_sec()
        entry = {
            "ts": event_ts,
            "values": {
                "rfid_card_event": {
                    "access_log_id": str(event_ts - 3000),
                    "lock_type": "ttlock",
                    "card_uid": random.choice(["Pasword unlock", "04A2B3C4D5", "Fingerprint unlock"]),
                    "open_type": "unknown",
                    "openResult": 1,
                    "event_ts": event_ts,
                }
            },
        }
        return {
            "sourceDeviceUUID": ctx.gateway_id,
            "topic": "v1/gateway/telemetry",
            "data": {ctx.name: [entry]},
        }

    def build_attributes(self, ctx: DeviceCtx) -> dict:
        values = {"dnd": random.choice([0, 1]), "gatewayOnline": random.choice([True, False])}
        if ctx.is_sub_device:
            return {
                "sourceDeviceUUID": ctx.gateway_id,
                "topic": "v1/gateway/attributes",
                "data": {ctx.name: values},
            }
        return {
            "sourceDeviceUUID": ctx.own_id,
            "topic": "v1/devices/me/attributes",
            "data": values,
        }

    def build_device_activity(self, ctx: DeviceCtx, *, connected: bool) -> dict:
        topic = "v1/gateway/connect" if connected else "v1/gateway/disconnect"
        return {
            "sourceDeviceUUID": ctx.gateway_id,
            "topic": topic,
            "data": {"device": ctx.name},
        }

    def build_attribute_request(self, ctx: DeviceCtx) -> dict:
        keys = random.sample(ATTRIBUTE_KEYS, k=random.randint(1, len(ATTRIBUTE_KEYS)))
        if ctx.is_sub_device:
            return {
                "sourceDeviceUUID": ctx.gateway_id,
                "topic": "v1/gateway/attributes/request",
                "data": {"device": ctx.name, "id": random.randint(1, 1000), "keys": keys},
            }
        return {
            "sourceDeviceUUID": ctx.own_id,
            "topic": "v1/devices/me/attributes/request",
            "data": {"id": random.randint(1, 1000), "keys": keys},
        }

    def build_rpc(self, ctx: DeviceCtx) -> dict:
        # NOTE: handle_rpc() updates the RPCMessage row whose id matches data.id.
        # With a random id no row is found, so this only exercises routing, not
        # the DB update — pass a real RPCMessage.id to test the full path.
        return {
            "sourceDeviceUUID": ctx.gateway_id,
            "topic": "v1/gateway/rpc",
            "data": {"id": random.randint(1, 1000), "data": {"success": True}},
        }
