import pytest
from channels.db import database_sync_to_async

from access_manager.models import Card, NeedSyncDevice
from main.models import Device

# A device of another tenant (karina@gmail.com is tenant 28c81921-...).
FOREIGN_DEVICE = "9829490d-f742-400e-8f38-aae5155e0b27"
OWN_DEVICE = "1829490d-f742-400e-8f48-aae5155e4b27"
KARINA_TENANT = "28c81921-f78e-4864-87d2-cec674f19d1c"


def _frame(stream, action, request_id, **payload):
    return {"stream": stream, "payload": {"action": action, "request_id": request_id, **payload}}


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestDeviceAccess:
    @pytest.mark.parametrize(
        ("stream", "action", "query_params"),
        [
            ("ts_kv_latest", "subscribe", {"device": FOREIGN_DEVICE}),
            ("ts_kv_latest", "list_subscribe", {"device": FOREIGN_DEVICE}),
            ("attributes", "subscribe", {"device": FOREIGN_DEVICE, "scope": "SERVER_SCOPE"}),
            ("attributes", "list_subscribe", {"device": FOREIGN_DEVICE, "scope": "SERVER_SCOPE"}),
            ("tag_logs", "list_subscribe", {"device": FOREIGN_DEVICE}),
            ("gateway_logs", "subscribe", {"device": FOREIGN_DEVICE}),
            ("ts_kv_history", "list_subscribe", {"device": FOREIGN_DEVICE}),
            ("ts_kv_latest", "subscribe", {"device": "not-a-uuid"}),
        ],
    )
    async def test_foreign_device_is_rejected(self, ws_connect, karina_token, stream, action, query_params):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_frame(stream, action, "r1", query_params=query_params))
            reply = await comm.receive_json_from(timeout=5)
            assert reply["stream"] == stream
            assert reply["payload"]["request_id"] == "r1"
            assert reply["payload"]["response_status"] == 400
        finally:
            await comm.disconnect()

    async def test_own_device_is_allowed(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_frame("ts_kv_latest", "list_subscribe", "r1", query_params={"device": OWN_DEVICE}))
            reply = await comm.receive_json_from(timeout=5)
            assert reply["payload"]["response_status"] == 200
        finally:
            await comm.disconnect()


@pytest.fixture
@database_sync_to_async
def foreign_need_sync():
    card = Card.objects.filter(tenant_id=KARINA_TENANT).first()
    foreign = Device.objects.get(pk=FOREIGN_DEVICE)
    return NeedSyncDevice.objects.create(device=foreign, card=card)


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestNeedSyncTenant:
    async def test_list_excludes_other_tenants(self, ws_connect, karina_token, foreign_need_sync):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_frame("need_sync", "list_subscribe", "ns1", query_params={}))
            reply = await comm.receive_json_from(timeout=5)
            results = reply["payload"]["data"]["results"]
            assert all(row["device_name"] != foreign_need_sync.device.name for row in results)
        finally:
            await comm.disconnect()
