import logging
from datetime import datetime, timedelta

from django.utils import timezone
from mews.client import MewsAPIClient
from mews.management.commands.mews_access_tokens import MewsConfigAdapter
from mews.models import MewsConfiguration

from services.models import Integration
from services.utils.const import MEWS
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
            logger.debug("Skipping non-MUR relay event: %s", ts_kv_latest.key.key)
            return

        if str(ts_kv_latest.get_value) != "1":
            logger.debug("Skipping MUR relay with value: %s", ts_kv_latest.get_value)
            return

        if not ts_kv_latest.entity or not ts_kv_latest.entity.room:
            logger.warning("MUR relay event without room: entity_id=%s", ts_kv_latest.entity_id)
            return

        room = ts_kv_latest.entity.room
        tenant = room.tenant

        mews_integration = (
            Integration.objects.filter(
                tenant=tenant,
                integrator__name__iexact=MEWS,
                integrator__client_id__isnull=False,
                enable=True,
                is_active=True,
            )
            .select_related("tenant")
            .first()
        )
        mews_pms_send_tasks = mews_integration and (mews_integration.additional_info or {}).get("send_tasks")

        if not mews_pms_send_tasks:
            logger.info("Mews PMS integration or task sending not enabled for tenant %s", tenant.title)
            return

        guest = room.guests.filter(is_active=True).first()
        if not guest:
            logger.info("No active guest in room %s, skipping MUR relay", room.number)
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
                        "MUR relay triggered too soon for room %s. Last trigger: %s, skipping",
                        room.number,
                        last_mur_relay,
                    )
                    return
            except (ValueError, TypeError) as e:
                logger.warning("Invalid mews_mur_relay timestamp format: %s", e)

        try:
            mews_config = MewsConfigAdapter(mews_integration)
        except MewsConfiguration.DoesNotExist:
            logger.info("Mews integration not configured or inactive for tenant %s", ts_kv_latest.entity.tenant.title)
            return

        mews_reservation_id = guest.additional_info.get("mews_reservation_id")
        if not mews_reservation_id:
            logger.warning("Guest %s in room %s has no mews_reservation_id", guest.id, room.number)
            return

        client = MewsAPIClient(
            client_token=mews_config.client_token,
            access_token=mews_config.access_token,
            base_url=mews_config.api_base_url,
        )

        deadline_utc = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "ServiceOrderId": mews_reservation_id,
            "Name": "MUR",
            "DeadlineUtc": deadline_utc,
        }

        logger.info(
            "Sending MUR task to Mews for room %s, guest %s, reservation %s",
            room.number,
            guest.name,
            mews_reservation_id,
        )

        response = client._make_request("tasks/add", params)

        logger.info("MUR task successfully created in Mews: %s", response)

        guest.additional_info["mews_mur_relay"] = timezone.now().isoformat()
        guest.save(update_fields=["additional_info"])

        logger.info("Updated mews_mur_relay timestamp for guest %s", guest.id)

    except Exception:
        logger.exception("Error publishing MUR relay to Mews")
