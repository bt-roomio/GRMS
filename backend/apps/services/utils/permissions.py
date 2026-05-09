import logging

from django.conf import settings

from rest_framework import permissions

from services.models import Integration

logger = logging.getLogger(__name__)


class DoorLockPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        client_token = request.headers.get("ClientToken")
        access_token = request.headers.get("AccessToken")

        if not client_token or not access_token:
            return False

        if client_token not in settings.CLIENT_TOKENS:
            return False

        try:
            integration = Integration.objects.get(access_token=access_token)
        except Integration.DoesNotExist:
            return False
        except Integration.MultipleObjectsReturned:
            logger.error("Integartion AccessToken is not unique.")
            return False

        request.tenant = integration.tenant
        return True
