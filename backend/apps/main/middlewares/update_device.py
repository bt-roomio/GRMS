from django.utils.deprecation import MiddlewareMixin

from main.metrics import update_device_metrics


class UpdateDeviceMetricsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path == "/metrics":
            update_device_metrics()
        return None
