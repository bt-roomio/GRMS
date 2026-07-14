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
    Основная функция обновления всех метрик устройств
    Вызывается автоматически при каждом запросе к /metrics
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
    Очистка всех метрик перед обновлением
    Note: .clear() не работает в multiprocess mode, поэтому мы явно обнуляем метрики
    """
    excluded_gateways = settings.DJANGO_MONITORING_EXCLUDED_GATEWAYS

    if excluded_gateways:
        logger.info(f"Исключено gateway устройств из мониторинга: {len(excluded_gateways)} ({excluded_gateways})")

    # Получаем все активные gateway устройства (включая excluded — чтобы сбросить stale данные)
    all_combinations = list(
        Device.objects.filter(is_active=True, additional_info__gateway=True)
        .select_related("tenant")
        .values("tenant_id", "tenant__title", "id")
        .distinct()
    )

    # Явно обнуляем все известные метрики (включая excluded, чтобы stale значения не оставались)
    for combo in all_combinations:
        tenant_id = str(combo["tenant_id"])
        tenant_name = _sanitize_label(combo["tenant__title"] or "Unknown")
        device_id = str(combo["id"])

        devices_offline_total.labels(tenant_id=tenant_id, tenant_name=tenant_name, device_id=device_id).set(0)

    # Обнуляем агрегированную метрику
    offline_gateway_devices_count.set(0)

    return all_combinations


def _zero_stale_metrics(current_combinations) -> None:
    """
    Обнуляет devices_offline_total для gateway устройств, которые были удалены
    или деактивированы с прошлого обновления.

    prometheus_client в multiprocess-режиме не умеет удалять лейблсеты
    (.remove() — no-op), поэтому метрика устройства, которое было offline,
    после удаления из БД навсегда "застревает" со значением 1 в gauge_*.db.
    Здесь мы помним предыдущий набор gateway устройств в Redis и при исчезновении
    устройства явно перезаписываем его метрику в 0 — это перекрывает stale-запись
    благодаря multiprocess_mode="mostrecent" (выигрывает запись с более новым timestamp).
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
    """Обновление метрик статуса устройств"""

    excluded_gateways = settings.DJANGO_MONITORING_EXCLUDED_GATEWAYS

    # Получаем все offline gateway устройства
    query = Device.objects.filter(is_active=True, additional_info__gateway=True, status=False)

    # Исключаем gateway из списка исключений (если список не пустой)
    if excluded_gateways:
        query = query.exclude(id__in=excluded_gateways)

    offline_devices = query.select_related("tenant").values("tenant_id", "tenant__title", "id")

    for device in offline_devices:
        tenant_id = str(device["tenant_id"])
        tenant_name = _sanitize_label(device["tenant__title"] or "Unknown")
        device_id = str(device["id"])

        # Устанавливаем метрику в 1 для offline устройства
        devices_offline_total.labels(tenant_id=tenant_id, tenant_name=tenant_name, device_id=device_id).set(1)

    # Обновляем агрегированную метрику (общее количество offline gateway устройств)
    total_offline_query = Device.objects.filter(is_active=True, additional_info__gateway=True, status=False)

    # Применяем исключения для агрегированной метрики
    if excluded_gateways:
        total_offline_query = total_offline_query.exclude(id__in=excluded_gateways)

    total_offline = total_offline_query.count()
    offline_gateway_devices_count.set(total_offline)
