import logging
from collections import defaultdict

from django.core.management.base import BaseCommand

from core.utils.get_time import get_mil_sec
from shuttle.models import AttributeKv, Relation
from shuttle.services.attribute_kv import publish_updates_attribute_batch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command for monitoring gateway device activity.

    Checks the activity status of gateway devices and marks inactive gateways
    and their related devices as inactive when they haven't communicated within
    the expected timeframe (60 seconds).

    This command is designed to be run periodically via Celery Beat every 10 seconds.

    Usage:
        ./manage.py active_attribute_server_scope

    Note:
        Typically invoked automatically via Celery Beat task.
    """

    help = "Check and update inactive gateway devices (SERVER_SCOPE)"

    # Inactivity threshold in milliseconds (60 seconds)
    INACTIVITY_THRESHOLD_MS = 60000

    def handle(self, *args, **options):
        """
        Retrieve and check activity status of all gateway devices.

        Queries all AttributeKv records for gateway devices with 'active' attribute
        and passes them to activity time verification.

        The function specifically targets devices marked as gateways in their
        additional_info field and checks their active attribute status.
        """
        logger.info("Starting active_attribute_server_scope command")

        try:
            # Fetch active gateway devices with related entity data
            gateway_active_attrs = list(
                AttributeKv.objects.select_related("entity").filter(
                    entity__additional_info__gateway=True, attribute_key="active", bool_v=True
                )
            )

            if not gateway_active_attrs:
                logger.debug("No active gateway devices found")
                return

            logger.debug(f"Found {len(gateway_active_attrs)} active gateway devices to check")

            # Process inactive devices
            deactivated, related_deactivated = self.check_activity_time(gateway_active_attrs)

            # Log summary
            if deactivated > 0:
                logger.info(f"Deactivated {deactivated} gateway device(s) and {related_deactivated} related device(s)")
            else:
                logger.debug("No inactive gateway devices found")

            logger.info("Completed active_attribute_server_scope command")

        except Exception as e:
            logger.error(f"Error in active_attribute_server_scope command: {e}", exc_info=True)
            raise

    def check_activity_time(self, gateway_active_attrs):
        """
        Verify device activity and deactivate inactive devices.

        Checks the lastActivityTime attribute for each device. If a device hasn't
        been active for more than 60 seconds (60000 milliseconds), it marks both
        the device and its 'active' attribute as inactive.

        For gateway devices, this function also deactivates all related devices
        connected through the Relation model, ensuring cascading deactivation.

        Args:
            gateway_active_attrs: List of AttributeKv objects representing 'active'
                                attributes for gateway devices.

        Returns:
            tuple: (deactivated_count, related_deactivated_count)

        Side Effects:
            - Updates AttributeKv.bool_v to False for inactive devices
            - Updates Entity.status to False for inactive devices
            - Cascades deactivation to related devices for gateways
            - Logs device IDs of deactivated devices (WARNING level for gateways,
              INFO level for related devices)
            - Publishes WebSocket updates for deactivated devices
        """
        current_time = get_mil_sec()
        threshold_time = current_time - self.INACTIVITY_THRESHOLD_MS

        # Extract entity IDs for batch query
        entity_ids = [attr.entity_id for attr in gateway_active_attrs]

        # Fetch all lastActivityTime attributes in one query
        last_activity_attrs = {
            attr.entity_id: attr
            for attr in AttributeKv.objects.filter(entity_id__in=entity_ids, attribute_key="lastActivityTime")
        }

        # Lists to collect objects for bulk updates
        attrs_to_update = []
        entities_to_update = []
        inactive_gateway_ids = []

        # Identify inactive gateways
        for attr_active in gateway_active_attrs:
            last_activity_attr = last_activity_attrs.get(attr_active.entity_id)

            if not last_activity_attr:
                logger.warning(f"Missing lastActivityTime for gateway device: {attr_active.entity_id}")
                continue

            # Check if device is inactive
            if last_activity_attr.long_v < threshold_time:
                logger.warning(
                    f"Deactivated gateway device: {attr_active.entity_id} "
                    f"(last activity: {(current_time - last_activity_attr.long_v) / 1000:.0f}s ago)"
                )

                # Mark for deactivation
                attr_active.bool_v = False
                attrs_to_update.append(attr_active)

                attr_active.entity.status = False
                entities_to_update.append(attr_active.entity)

                inactive_gateway_ids.append(attr_active.entity_id)

        # Bulk update gateway attributes and entities
        if attrs_to_update:
            AttributeKv.objects.bulk_update(attrs_to_update, ["bool_v"])
            # Update entities individually due to potential for different entity types
            for entity in entities_to_update:
                entity.save(update_fields=["status"])

            # Publish WebSocket updates for deactivated gateways
            self._publish_deactivation_updates(attrs_to_update, current_time)

        # Handle related devices for inactive gateways
        related_deactivated = 0
        if inactive_gateway_ids:
            related_deactivated = self._deactivate_related_devices(inactive_gateway_ids)

        return len(attrs_to_update), related_deactivated

    def _publish_deactivation_updates(self, attrs_to_update, current_time):
        """
        Publish WebSocket updates for deactivated devices.

        Args:
            attrs_to_update: List of AttributeKv objects that were updated
            current_time: Current timestamp in milliseconds
        """
        if not attrs_to_update:
            return

        updates_by_device = defaultdict(list)

        for attr in attrs_to_update:
            # Get tenant_id from the entity relation
            tenant_id = attr.entity.tenant_id
            device_key = f"{attr.entity_id}_{tenant_id}"

            logger.info(f"Current time: {current_time}")
            # Add update message for this device
            updates_by_device[device_key].append(
                {
                    "entity": str(attr.entity_id),
                    "key_name": attr.attribute_key,
                    "last_update_ts": current_time,
                    "scope": AttributeKv.SERVER_SCOPE,
                    "value": attr.bool_v,
                }
            )

        if updates_by_device:
            try:
                publish_updates_attribute_batch(updates_by_device)
                logger.debug(f"Published WebSocket updates for {len(updates_by_device)} deactivated gateway devices")
            except Exception as e:
                logger.error(f"Failed to publish WebSocket updates: {e}", exc_info=True)

    def _deactivate_related_devices(self, gateway_ids):
        """
        Deactivate all devices related to the given gateway IDs.

        Args:
            gateway_ids: List of gateway entity IDs

        Returns:
            int: Number of related devices deactivated
        """
        # Get all related device IDs in one query
        related_device_ids = list(Relation.objects.filter(from_id__in=gateway_ids).values_list("to_id_id", flat=True))

        if not related_device_ids:
            return 0

        # Fetch all active attributes for related devices
        related_attrs = AttributeKv.objects.select_related("entity").filter(
            entity_id__in=related_device_ids, attribute_key="active", bool_v=True
        )

        # Prepare for bulk update
        attrs_to_update = []
        entities_to_update = []

        for relation_attr in related_attrs:
            logger.info(f"Deactivated related device: {relation_attr.entity_id}")
            relation_attr.bool_v = False
            attrs_to_update.append(relation_attr)

            relation_attr.entity.status = False
            entities_to_update.append(relation_attr.entity)

        # Bulk update
        if attrs_to_update:
            current_time = get_mil_sec()
            AttributeKv.objects.bulk_update(attrs_to_update, ["bool_v"])
            for entity in entities_to_update:
                entity.save(update_fields=["status"])

            # Publish WebSocket updates for deactivated related devices
            self._publish_deactivation_updates(attrs_to_update, current_time)

        return len(attrs_to_update)
