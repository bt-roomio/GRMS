"""Async версия publish_room_status для использования в асинхронном контексте (mq_async.py)"""

from channels.layers import get_channel_layer

from main.models import Device


async def publish_room_status_async(instance: Device):
    """Асинхронная версия publish_room_status для использования в async контексте"""
    channel_layer = get_channel_layer()

    if not channel_layer:
        return

    await channel_layer.group_send(
        f"room_status_{instance.tenant_id}",
        {
            "type": "get_latest_activity",
            "update": {"tenant_id": str(instance.tenant_id)},
        },
    )
