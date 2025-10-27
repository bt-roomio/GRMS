import logging

from django.conf import settings
from django.db import DatabaseError
from prometheus_client import Gauge

from main.models import Device

logger = logging.getLogger(__name__)

# Gauges для мониторинга устройств
offline_gateway_devices = Gauge(
    "offline_gateway_devices_total",
    "Number of gateway devices with status False",
    ["tenant_id", "tenant_name", "device_id", "device_name"],
    multiprocess_mode="max",
)

offline_gateway_devices_simple = Gauge(
    "offline_gateway_devices_count",
    "Total count of offline gateway devices",
    multiprocess_mode="max",
)


IS_MONITORINT_GATEWAYS = settings.DJANGO_IS_MONITORING_GATEWAYS
MONITOR_DISABLED_GATEWAYS = settings.DJANGO_MONITOR_DISABLED_GATEWAYS


def update_device_metrics() -> None:
    """
    Update Prometheus metrics for devices.
    This function should be called periodically.
    Reads device status from database and updates Prometheus gauges.
    """
    try:
        if not IS_MONITORINT_GATEWAYS:
            return
        # Получаем список оффлайн шлюзов
        offline_gateways = Device.objects.filter(
            status=False,
            additional_info__gateway=True,
            is_active=True,
        ).select_related("tenant")

        if MONITOR_DISABLED_GATEWAYS:
            offline_gateways = offline_gateways.exclude(id__in=MONITOR_DISABLED_GATEWAYS)

        # Подсчитываем общее количество
        total_count = offline_gateways.count()
        offline_gateway_devices_simple.set(total_count)

        logger.debug(f"Total offline gateway devices: {total_count}")

        # Сначала собираем все активные лейблы
        active_labels = set()
        for device in offline_gateways:
            label_values = (
                str(device.tenant_id),
                device.tenant.title,
                str(device.id),
                device.name,
            )
            active_labels.add(label_values)
            offline_gateway_devices.labels(
                tenant_id=label_values[0],
                tenant_name=label_values[1],
                device_id=label_values[2],
                device_name=label_values[3],
            ).set(1)

        # Сбрасываем метрики для устройств, которых больше нет в списке оффлайн
        # Примечание: _metrics.clear() очищает все метрики, что может быть нежелательно
        # при параллельных запросах. Лучше использовать явное обнуление или
        # полагаться на TTL метрик в Prometheus.

        logger.debug(f"Updated metrics for {len(active_labels)} offline gateway devices")

    except DatabaseError as e:
        logger.error(f"Database error while updating device metrics: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while updating device metrics: {e}", exc_info=True)
