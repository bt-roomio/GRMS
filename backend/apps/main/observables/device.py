import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from main.models import Device
from main.serializers.device import SimpleDeviceSerializer

logger = logging.getLogger(__name__)


def publish_device(instance: Device):
    channel_layer = get_channel_layer()

    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f"device_{instance.tenant_id}",
        {
            "type": "get_latest_activity",
            "update": SimpleDeviceSerializer(instance).data,
        },
    )
    logger.debug(f"✓ Published device changes {instance.name}")
