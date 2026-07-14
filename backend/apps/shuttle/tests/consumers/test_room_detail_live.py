import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer

from main.models import Room
from shuttle.constants import STATIC_KEYS


@pytest.fixture
@database_sync_to_async
def test_room():
    return Room.objects.get(pk="df77f910-2dcd-45cf-b6be-054c744561a7")


def _telemetry_update(device_id, key, value):
    return {
        "entity": str(device_id),
        "key": key,
        "ts": 1,
        "bool_v": None,
        "str_v": None,
        "long_v": None,
        "dbl_v": value,
        "json_v": None,
        "value": value,
    }


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestRoomDetailLive:
    async def _subscribe(self, comm, room, request_id):
        await comm.send_json_to(
            {
                "stream": "room_detail",
                "payload": {"action": "subscribe", "request_id": request_id, "pk": str(room.id)},
            }
        )
        reply = await comm.receive_json_from()
        return (reply.get("payload") or {}).get("data") or {}

    @pytest.mark.parametrize("device_index", [0, 1])
    async def test_ts_kv_latest_activity_updates_any_room_device(
        self, ws_connect, karina_token, test_room, device_index
    ):
        """Телеметрия должна доходить с любого устройства комнаты, а не только с первого."""
        comm = await ws_connect(karina_token)
        try:
            data = await self._subscribe(comm, test_room, "live1")
            devices = data.get("devices") or []
            assert len(devices) > device_index, "недостаточно устройств у комнаты для теста"
            device_id = devices[device_index]["id"]

            key = STATIC_KEYS[3]  # Room Temperature
            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                f"tskv_latest_updates_{device_id}",
                {"type": "ts_kv_latest_activity", "updates": [_telemetry_update(device_id, key, 25.5)]},
            )

            live = await comm.receive_json_from(timeout=5)
            telemetry = ((live.get("payload") or {}).get("data") or {}).get("telemetry") or {}
            assert telemetry.get(key) == 25.5, f"telemetry не обновилась: {telemetry}"
        finally:
            await comm.disconnect()
