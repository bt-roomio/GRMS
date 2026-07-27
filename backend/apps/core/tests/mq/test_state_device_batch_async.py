"""Unit tests for sync_state_device_batch_async (id-guard on cached attrs, create-guard on cache write).

All I/O (sub-device resolution, Redis attribute cache, AttributeKv/Device managers, WebSocket
publish) is mocked, so these run without a database. AttributeKv/Device model classes stay real
(only their ``.objects`` managers are patched) so constructed instances keep real ``.pk``/field
semantics — that is exactly what the bulk_update pk-guard depends on.
"""

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from core.management.mq.handlers import state_device_batch_async as sad
from shuttle.models import AttributeKv


def _patch_io(stack: ExitStack, cache: dict, sub_id: str = "d1", db_attrs=None, device_rows=None):
    """Patch every external dependency; return the namespace of installed mocks."""
    ns = MagicMock()

    ns.get_sub_device = stack.enter_context(
        patch.object(sad, "get_sub_device", return_value={"id": sub_id, "tenant_id": "t1"})
    )
    stack.enter_context(patch.object(sad, "close_old_connections", MagicMock()))
    stack.enter_context(patch.object(sad, "get_cached_attributes_batch", return_value=cache))
    stack.enter_context(patch.object(sad, "invalidate_attributes_cache", MagicMock()))
    stack.enter_context(patch.object(sad, "invalidate_quick_cache", MagicMock()))
    ns.set_cached_attributes = stack.enter_context(patch.object(sad, "set_cached_attributes", MagicMock()))
    ns.publish_updates = stack.enter_context(
        patch.object(sad, "publish_updates_attribute_batch_async", new=AsyncMock())
    )
    stack.enter_context(patch.object(sad, "publish_room_status_async", new=AsyncMock()))
    stack.enter_context(patch.object(sad, "publish_device", MagicMock()))

    attr_objs = MagicMock()
    attr_objs.filter.return_value.order_by.return_value = db_attrs or []
    ns.attr_objs = stack.enter_context(patch.object(sad.AttributeKv, "objects", attr_objs))

    dev_objs = MagicMock()
    dev_objs.filter.return_value.values.return_value = device_rows or []
    ns.dev_objs = stack.enter_context(patch.object(sad.Device, "objects", dev_objs))

    return ns


async def test_cached_attr_with_id_is_used_for_bulk_update():
    """Cache hit carrying 'id' → the object goes into bulk_update WITH a pk (no ValueError)."""
    cache = {
        "d1": {
            "active": {"id": "a1", "bool_v": False, "last_update_ts": 1, "tenant_id": "t1", "status": True},
            "lastActivityTime": {"id": "l1", "long_v": 1, "last_update_ts": 1, "tenant_id": "t1"},
        }
    }
    with ExitStack() as stack:
        ns = _patch_io(stack, cache)
        # gateway connect → active flips False→True, so active goes to to_update
        await sad.sync_state_device_batch_async(
            [({"id": "gw", "tenant_id": "t1"}, "v1/gateway/connect", {"device": "sub"})]
        )

    ns.attr_objs.bulk_update.assert_called_once()
    updated = ns.attr_objs.bulk_update.call_args[0][0]
    assert updated, "expected at least one attribute to update"
    assert all(obj.pk is not None for obj in updated)  # the fix: never an id-less object in bulk_update
    ns.attr_objs.bulk_create.assert_not_called()  # both attrs already existed


async def test_cached_attr_without_id_falls_back_to_db_and_never_bulk_updates_pkless():
    """Cache hit missing 'id' → treated as miss, read from DB; no id-less object reaches bulk_update."""
    cache = {
        "d1": {
            "active": {"bool_v": False, "last_update_ts": 1, "tenant_id": "t1", "status": True},  # no "id"
            "lastActivityTime": {"long_v": 1, "last_update_ts": 1, "tenant_id": "t1"},  # no "id"
        }
    }
    with ExitStack() as stack:
        ns = _patch_io(stack, cache, db_attrs=[])  # DB also returns nothing
        await sad.sync_state_device_batch_async(
            [({"id": "gw", "tenant_id": "t1"}, "v1/gateway/connect", {"device": "sub"})]
        )

    # Fell back to the DB query for the id-less cache entry ...
    ns.attr_objs.filter.assert_called()
    # ... and since DB had nothing, both attrs are created — never an id-less bulk_update (the bug).
    ns.attr_objs.bulk_update.assert_not_called()
    ns.attr_objs.bulk_create.assert_called_once()


async def test_created_attrs_are_not_written_to_cache():
    """Fresh device (cache + DB miss) → bulk_create, but its client-generated (None) ids are NOT cached."""
    with ExitStack() as stack:
        ns = _patch_io(stack, cache={"d1": None}, db_attrs=[])
        await sad.sync_state_device_batch_async(
            [({"id": "gw", "tenant_id": "t1"}, "v1/gateway/connect", {"device": "sub"})]
        )

    ns.attr_objs.bulk_create.assert_called_once()
    ns.set_cached_attributes.assert_not_called()  # devices_with_creates guard


async def test_empty_batch_is_noop():
    with ExitStack() as stack:
        ns = _patch_io(stack, cache={})
        await sad.sync_state_device_batch_async([])
    ns.attr_objs.bulk_update.assert_not_called()
    ns.attr_objs.bulk_create.assert_not_called()


def test_attributekv_instance_from_cache_reports_pk():
    """Guards the assumption the fix relies on: setting id makes .pk non-None on an unsaved instance."""
    attr = AttributeKv(id="a1", entity_id="d1", attribute_key="active", attribute_type=AttributeKv.SERVER_SCOPE)
    assert attr.pk == "a1"
