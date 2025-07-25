from django.conf import settings
from prometheus_client import Gauge

from main.models import Device

offline_gateway_devices = Gauge(
    "offline_gateway_devices_total",
    "Number of gateway devices with status False",
    ["tenant_id", "tenant_name", "device_id", "device_name"],
)

offline_gateway_devices_simple = Gauge("offline_gateway_devices_count", "Total count of offline gateway devices")


def update_device_metrics():
    """
    Update Prometheus metrics for devices.
    This function should be called periodically.
    """
    offline_gateway_devices._metrics.clear()

    offline_gateways = Device.objects.filter(
        status=False, additional_info__gateway=True, is_active=True, id__in=settings.DJANGO_GATEWAYS_MONITORING
    ).select_related("tenant")

    offline_gateway_devices_simple.set(offline_gateways.count())

    for device in offline_gateways:
        offline_gateway_devices.labels(
            tenant_id=str(device.tenant_id),
            tenant_name=device.tenant.title,
            device_id=str(device.id),
            device_name=device.name,
        ).set(1)
