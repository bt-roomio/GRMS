import logging
from datetime import datetime, timedelta

from django.utils import timezone
from mews.client import MewsAPIClient
from mews.models import MewsConfiguration

from shuttle.models import TsKvLatest

logger = logging.getLogger(__name__)


def publish_mur_relay_to_mews(ts_kv_latest: TsKvLatest):
    """
    Обработчик срабатывания MUR (Make Up Room) реле

    При срабатывании MUR:
    1. Проверяет включена ли интеграция с PMS
    2. Проверяет включена ли интеграция с Mews
    3. Проверяет активирована ли опция создания задач уборки
    4. Проверяет не было ли срабатывания MUR в последние 3 минуты
    5. Отправляет задачу на уборку в Mews

    Args:
        ts_kv_latest: Последнее значение телеметрии с MUR Relay
    """
    try:
        if ts_kv_latest.key.key != "MUR Relay":
            logger.debug(f"Skipping non-MUR relay event: {ts_kv_latest.key.key}")
            return

        if str(ts_kv_latest.get_value) != "1":
            logger.debug(f"Skipping MUR relay with value: {ts_kv_latest.get_value}")
            return

        if not ts_kv_latest.entity or not ts_kv_latest.entity.room:
            logger.warning(f"MUR relay event without room: entity_id={ts_kv_latest.entity_id}")
            return

        room = ts_kv_latest.entity.room
        tenant = room.tenant

        mews_pms = (
            isinstance(tenant.additional_info, dict)
            and tenant.additional_info.get("integration_settings", {}).get("mews", {})
            or {}
        )
        mews_pms_enabled = mews_pms.get("enabled")
        mews_pms_send_tasks = mews_pms.get("send_tasks")

        if not (mews_pms_enabled or mews_pms_send_tasks):
            logger.info(f"Mews PMS integration or task sending not enabled for tenant {tenant.title}")
            return

        guest = room.guests.filter(is_active=True).first()
        if not guest:
            logger.info(f"No active guest in room {room.number}, skipping MUR relay")
            return

        if not guest.additional_info:
            guest.additional_info = {}

        # if ts_kv_latest.entity.tenant.additional_info
        last_mur_relay = guest.additional_info.get("mews_mur_relay")
        if last_mur_relay:
            try:
                last_mur_time = datetime.fromisoformat(last_mur_relay.replace("Z", "+00:00"))
                if timezone.now() < last_mur_time + timedelta(minutes=3):
                    logger.info(
                        f"MUR relay triggered too soon for room {room.number}. "
                        f"Last trigger: {last_mur_relay}, skipping"
                    )
                    return
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid mews_mur_relay timestamp format: {e}")

        try:
            mews_config = MewsConfiguration.objects.get(tenant=ts_kv_latest.entity.tenant, is_active=True)
        except MewsConfiguration.DoesNotExist:
            logger.info(f"Mews integration not configured or inactive for tenant {ts_kv_latest.entity.tenant.title}")
            return

        mews_reservation_id = guest.additional_info.get("mews_reservation_id")
        if not mews_reservation_id:
            logger.warning(f"Guest {guest.id} in room {room.number} has no mews_reservation_id")
            return

        client = MewsAPIClient(
            client_token=mews_config.client_token,
            access_token=mews_config.access_token,
            base_url=mews_config.api_base_url,  # pyright: ignore
        )

        deadline_utc = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "ServiceOrderId": mews_reservation_id,
            "Name": "MUR",
            "DeadlineUtc": deadline_utc,
        }

        logger.info(
            f"Sending MUR task to Mews for room {room.number}, guest {guest.name}, "
            f"reservation {mews_reservation_id}"
        )

        response = client._make_request("tasks/add", params)

        logger.info(f"MUR task successfully created in Mews: {response}")

        guest.additional_info["mews_mur_relay"] = timezone.now().isoformat()
        guest.save(update_fields=["additional_info"])

        logger.info(f"Updated mews_mur_relay timestamp for guest {guest.id}")

    except Exception as e:
        logger.error(f"Error publishing MUR relay to Mews: {e}", exc_info=True)
