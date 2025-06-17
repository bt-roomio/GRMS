from django.utils import timezone
from access_manager.models import CardLog, AccessGroupChoices, Card
import logging

from core.utils.date import unix_to_datetime

logger = logging.getLogger(__name__)


def handle_card_event(device, value, ts_dt):
    try:
        access_group_str = value.get('access_group', '').upper()
        card_uid = value.get('card_uid', '')
        event_ts_unix = value.get('event_ts')

        if not all([access_group_str, card_uid, event_ts_unix]):
            logger.warning(f"Missing required fields in RFID event: {value}")
            return None

        try:
            tenant = device.tenant
        except AttributeError:
            logger.error(f"Device object missing tenant attribute: {device}")
            return None

        access_group_value = getattr(AccessGroupChoices, access_group_str, AccessGroupChoices.FAILED)
        event_datetime = unix_to_datetime(event_ts_unix)

        staff = None
        guest = None

        try:
            card = Card.objects.filter(number=card_uid, tenant=tenant).first()

            if card:
                from access_manager.models import StaffCard
                staff_card = StaffCard.objects.filter(
                    card=card,
                    is_active=True
                ).select_related('staff').first()

                if staff_card:
                    staff = staff_card.staff
                else:
                    from access_manager.models import GuestCard
                    guest_card = GuestCard.objects.filter(
                        card=card,
                        is_active=True
                    ).select_related('guest').first()

                    if guest_card:
                        guest = guest_card.guest

        except Exception as e:
            logger.warning(f"Error finding staff/guest for card {card_uid}: {e}")

        card_log = CardLog(
            tenant=tenant,
            number=card_uid,
            event_ts=event_datetime,
            access_group=access_group_value,
            device=device,
            staff=staff,
            guest=guest,
            created_at=ts_dt,
            additional_info={
                'raw_event': value,
                'device_identifier': str(device),
                'processed_at': timezone.now().isoformat()
            }
        )
        return card_log

    except Exception as e:
        logger.error(f"Error processing RFID card event: {e}")
        logger.error(f"Device: {device}, Value: {value}, Timestamp: {ts_dt}")
        return None
