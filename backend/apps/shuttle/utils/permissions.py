from django.conf import settings
from hoteza.utils.permissions import WhiteListPermission

from main.models import AdminSettings


class WhiteListOrIsAuthenticated(WhiteListPermission):
    def has_permission(self, request, view):
        if bool(request.user and request.user.is_authenticated):
            return True

        admin_settings = AdminSettings.objects.first()
        admin_settings = admin_settings and admin_settings.json_value.get("hoteza_whitelist") or []

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # The X-Forwarded-For header can contain multiple IPs.
            # The first IP is usually the client’s public IP.
            remote_addr = x_forwarded_for.split(",")[0].strip()
        else:
            # If no proxy header is found, use REMOTE_ADDR.
            remote_addr = request.META.get("REMOTE_ADDR")

        for valid_ip in [*settings.HOTEZA_WHITELIST, *admin_settings]:
            if remote_addr == valid_ip or remote_addr.startswith(valid_ip):
                return True
        return False
