import logging

from access_manager.models import AccessGroupChoices, Card, CardLog
from django.utils import timezone

from core.utils.date import unix_to_datetime
from core.utils.update_funvil_last_log import update_lock_last_log_id

logger = logging.getLogger(__name__)


def resolve_card_holder_and_access_group(tenant_id, card_uid):
    staff = None
    guest = None
    access_group_from_holder = None

    if not card_uid:
        return staff, guest, access_group_from_holder

    try:
        card = Card.objects.filter(number=card_uid, tenant_id=tenant_id).first()
        if not card:
            return staff, guest, access_group_from_holder

        from access_manager.models import StaffCard, GuestCard



        guest_card = (
            GuestCard.objects.filter(card=card, is_active=True)
            .select_related("guest")
            .first()
        )
        if guest_card:
            guest = guest_card.guest
            access_group_from_holder = AccessGroupChoices.GUEST
        else:
            staff_card = (
                StaffCard.objects.filter(card=card, is_active=True)
                .select_related("staff__group")
                .first()
            )
            staff = staff_card.staff
            group = getattr(staff, "group", None)
            if group and group.group_type is not None:
                if group.group_type:
                    access_group_from_holder = group.group_type
                else:
                    access_group_from_holder = AccessGroupChoices.FAILED
            else:
                access_group_from_holder = AccessGroupChoices.FAILED

    except Exception as e:
        logger.warning(f"Error resolving holder for card {card_uid}: {e}")
    return staff, guest, access_group_from_holder


def handle_card_event(device, value, ts_dt):
    try:
        card_uid = value.get("card_uid", "")
        event_ts_unix = value.get("event_ts")
        access_log_id = value.get("access_log_id")
        lock_type = value.get("lock_type")
        is_access_log_id = bool(access_log_id)

        if not event_ts_unix:
            logger.warning(f"Missing event_ts in RFID event: {value}")
            return None

        try:
            tenant_id = device.get("tenant_id")
        except AttributeError:
            logger.error("Device object missing tenant attribute")
            return None

        event_datetime = unix_to_datetime(event_ts_unix)

        if not is_access_log_id:
            access_group_str = value.get("access_group", "").upper().replace(" ", "_")

            if not all([access_group_str, card_uid]):
                logger.warning(f"Missing required fields in RFID event: {value}")
                return None

            access_group_value = getattr(
                AccessGroupChoices, access_group_str, AccessGroupChoices.FAILED
            )
            staff, guest, access_group_from_holder = resolve_card_holder_and_access_group(tenant_id, card_uid)
            number_value = card_uid

        else:
            open_result = value.get("openResult")
            open_type = value.get("open_type")
            update_lock_last_log_id(tenant_id, access_log_id, lock_type, device)

            if open_result is None:
                logger.warning(f"Missing openResult in Fanvil RFID event: {value}")
                return None

            if not card_uid:
                number_value = open_type or ""
                staff, guest = None, None
                access_group_value = (AccessGroupChoices.HOUSEKEEPING if open_result else AccessGroupChoices.DENIED)
            else:
                number_value = card_uid
                staff, guest, access_group_from_holder = resolve_card_holder_and_access_group(tenant_id, card_uid)

                if not open_result:
                    access_group_value = AccessGroupChoices.DENIED
                else:
                    access_group_value = access_group_from_holder or AccessGroupChoices.FAILED

        additional_info = {
            "raw_event": value,
            "device_identifier": device.get("name"),
            "processed_at": timezone.now().isoformat(),
        }

        if is_access_log_id:
            additional_info.update(
                {
                    f"{lock_type}_access_log_id": access_log_id,
                    "open_type": value.get("open_type"),
                    "open_result": value.get("openResult"),
                    "display_name": value.get("displayName"),
                }
            )

        card_log = CardLog(
            tenant_id=tenant_id,
            number=number_value,
            event_ts=event_datetime,
            access_group=access_group_value,
            device_id=device.get("id"),
            staff=staff,
            guest=guest,
            created_at=ts_dt,
            additional_info=additional_info,
        )
        print(f"card : {card_log}")

        return card_log

    except Exception as e:
        logger.error(f"Error processing RFID card event: {e}")
        logger.error(
            f'Device: {device.get("id") if isinstance(device, dict) else device}, '
            f"Value: {value}, Timestamp: {ts_dt}"
        )
        return None