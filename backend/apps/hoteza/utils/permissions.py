import logging

from django.conf import settings

from rest_framework import exceptions, permissions

from core.utils.ip import get_client_ip

logger = logging.getLogger(__name__)


class WhiteListPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        from main.models import AdminSettings

        admin_settings = AdminSettings.objects.first()
        admin_settings_hoteza_whitelist = admin_settings and admin_settings.json_value.get("hoteza_whitelist", []) or []
        if not isinstance(admin_settings_hoteza_whitelist, list):
            admin_settings_hoteza_whitelist = []

        # Never read X-Forwarded-For here: its leftmost entry is client-controlled.
        remote_addr = get_client_ip(request)

        for valid_ip in [*settings.HOTEZA_WHITELIST, *admin_settings_hoteza_whitelist]:
            if remote_addr == valid_ip or remote_addr.startswith(valid_ip):
                return True
        logger.warning("IP %s is not allowed", remote_addr)
        raise exceptions.PermissionDenied(detail="Your IP address is not allowed.")
