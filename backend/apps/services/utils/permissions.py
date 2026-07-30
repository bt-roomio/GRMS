import logging

from rest_framework import permissions

from services.models import Integration

logger = logging.getLogger(__name__)


class DoorLockPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        client_token = request.headers.get("ClientToken")
        access_token = request.headers.get("AccessToken")

        if not client_token or not access_token:
            return False

        try:
            integration = Integration.objects.get(
                access_token=access_token, integrator__client_id=client_token, is_active=True, enable=True
            )
        except Integration.DoesNotExist:
            return False
        except Integration.MultipleObjectsReturned:
            logger.error("Integartion AccessToken is not unique.")
            return False

        request.tenant = integration.tenant
        return True
