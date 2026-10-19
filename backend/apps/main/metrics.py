import logging
import re

from django.conf import settings
from django.core.cache import caches
from prometheus_client import Gauge

from main.models import Device

logger = logging.getLogger(__name__)

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def _sanitize_label(value: str) -> str:
    return _CONTROL_CHARS_RE.sub("", value)


KNOWN_GATEWAY_IDS_CACHE_KEY = "monitoring:known_gateway_device_ids"

devices_offline_total = Gauge(
    "devices_offline_total",
    "Total number of offline devices",
    ["tenant_id", "tenant_name", "device_id"],
    multiprocess_mode="mostrecent",
)

offline_gateway_devices_count = Gauge(
    "offline_gateway_devices_count",
    "Total count of offline gateway devices",
    multiprocess_mode="mostrecent",
)


def update_device_metrics() -> None:
    """
    Main function that updates all device metrics
    Called automatically on every request to /metrics
    """
    if not settings.DJANGO_IS_MONITORING_GATEWAYS:
        logger.debug("Мониторинг gateway устройств отключен (DJANGO_IS_MONITORING_GATEWAYS=False)")
        return

    try:
        all_combinations = _clear_metrics()
        _update_device_status_metrics()
        _zero_stale_metrics(all_combinations)
    except Exception as e:
        logger.error(f"Ошибка при обновлении метрик: {e}", exc_info=True)


def _clear_metrics():
    """
    Clear all metrics before updating
    Note: .clear() doesn't work in multiprocess mode, so we zero the metrics explicitly
    """
    excluded_gateways = settings.DJANGO_MONITORING_EXCLUDED_GATEWAYS

    if excluded_gateways:
        logger.info(f"Исключено gateway устройств из мониторинга: {len(excluded_gateways)} ({excluded_gateways})")

    # Get all active gateway devices (including excluded ones, to reset stale data)
    all_combinations = list(
        Device.objects.filter(is_active=True, additional_info__gateway=True)
        .select_related("tenant")
        .values("tenant_id", "tenant__title", "id")
        .distinct()
    )

    # Explicitly zero all known metrics (including excluded ones, so stale values don't linger)
    for combo in all_combinations:
        tenant_id = str(combo["tenant_id"])
        tenant_name = _sanitize_label(combo["tenant__title"] or "Unknown")
        device_id = str(combo["id"])

        devices_offline_total.labels(tenant_id=tenant_id, tenant_name=tenant_name, device_id=device_id).set(0)

    # Zero the aggregated metric
    offline_gateway_devices_count.set(0)

    return all_combinations


def _zero_stale_metrics(current_combinations) -> None:
    """
    Zeroes devices_offline_total for gateway devices that were deleted
    or deactivated since the previous update.

    prometheus_client in multiprocess mode can't remove label sets
    (.remove() is a no-op), so the metric of a device that was offline
    gets "stuck" at 1 in gauge_*.db forever after it is deleted from the DB.
    Here we remember the previous set of gateway devices in Redis and, when a device
    disappears, explicitly overwrite its metric with 0; this overrides the stale entry
    thanks to multiprocess_mode="mostrecent" (the entry with the newer timestamp wins).
    """
    cache = caches["default"]

    current_known = {
        str(combo["id"]): {
            "tenant_id": str(combo["tenant_id"]),
            "tenant_name": _sanitize_label(combo["tenant__title"] or "Unknown"),
        }
        for combo in current_combinations
    }
    previous_known = cache.get(KNOWN_GATEWAY_IDS_CACHE_KEY) or {}

    stale_device_ids = previous_known.keys() - current_known.keys()
    for device_id in stale_device_ids:
        info = previous_known[device_id]
        devices_offline_total.labels(
            tenant_id=info["tenant_id"], tenant_name=info["tenant_name"], device_id=device_id
        ).set(0)
        logger.info(f"Обнулена устаревшая метрика для удалённого/деактивированного gateway устройства {device_id}")

    cache.set(KNOWN_GATEWAY_IDS_CACHE_KEY, current_known, timeout=None)


def _update_device_status_metrics():
    """Update device status metrics"""

    excluded_gateways = settings.DJANGO_MONITORING_EXCLUDED_GATEWAYS

    # Get all offline gateway devices
    query = Device.objects.filter(
        is_active=True,
        status=False,
        additional_info__gateway=True,
    ).exclude(
        additional_info__has_key="excluded_monitoring",
        additional_info__excluded_monitoring=True,
    )

    # Drop gateways in the exclusion list (if the list is not empty)
    if excluded_gateways:
        query = query.exclude(id__in=excluded_gateways)

    offline_devices = query.select_related("tenant").values("tenant_id", "tenant__title", "id")

    for device in offline_devices:
        tenant_id = str(device["tenant_id"])
        tenant_name = _sanitize_label(device["tenant__title"] or "Unknown")
        device_id = str(device["id"])

        # Set the metric to 1 for an offline device
        devices_offline_total.labels(tenant_id=tenant_id, tenant_name=tenant_name, device_id=device_id).set(1)

    # Update the aggregated metric (total number of offline gateway devices)
    # Reuse the same query so filters/exclusions don't drift apart
    total_offline = query.count()
    offline_gateway_devices_count.set(total_offline)
