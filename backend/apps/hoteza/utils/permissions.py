import logging

from django.conf import settings

from rest_framework import exceptions, permissions

logger = logging.getLogger(__name__)


class WhiteListPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        from main.models import AdminSettings

        admin_settings = AdminSettings.objects.first()
        admin_settings_hoteza_whitelist = admin_settings and admin_settings.json_value.get("hoteza_whitelist", []) or []
        if not isinstance(admin_settings_hoteza_whitelist, list):
            admin_settings_hoteza_whitelist = []

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # The X-Forwarded-For header can contain multiple IPs.
            # The first IP is usually the client’s public IP.
            remote_addr = x_forwarded_for.split(",")[0].strip()
        else:
            # If no proxy header is found, use REMOTE_ADDR.
            remote_addr = request.META.get("REMOTE_ADDR")

        for valid_ip in [*settings.HOTEZA_WHITELIST, *admin_settings_hoteza_whitelist]:
            if remote_addr == valid_ip or remote_addr.startswith(valid_ip):
                return True
        logger.warning("IP %s is not allowed", remote_addr)
        raise exceptions.PermissionDenied(detail="Your IP address is not allowed.")
