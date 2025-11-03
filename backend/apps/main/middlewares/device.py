import logging

from main.metrics import update_device_metrics

logger = logging.getLogger(__name__)


class DeviceMetricsMiddleware:
    """
    Middleware для обновления метрик устройств при запросе к /metrics
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/metrics":
            logger.info("Обновление метрик устройств...")
            update_device_metrics()

        response = self.get_response(request)
        return response
