"""
Periodic notification dispatcher.

Driven entirely by the ``Alarm`` table — no watermark, no queue — so running it
twice in a row is a no-op the second time. Grouping one message per tenant is
what keeps a gateway outage from becoming forty Telegram messages, and the
``notify_delay_sec`` window is what keeps a flapping link quiet.
"""

import html
import logging
from datetime import datetime, timedelta

from django.core.cache import caches
from django.utils import timezone

from alarms.channels.telegram import TelegramChannel
from alarms.constants import AlarmSeverity
from alarms.models import Alarm
from alarms.notifications.settings import SETTINGS_KEY, allowed_severities, notification_settings
from alarms.telegram.exceptions import TelegramAPIError, TelegramNotConfigured
from main.models import Tenant

logger = logging.getLogger(__name__)

MAX_LINES = 20
# Telegram allows roughly 20 messages a minute to one chat; stay well under it.
RATE_LIMIT_PER_MINUTE = 10

SEVERITY_ICONS = {
    AlarmSeverity.CRITICAL: "🔴",
    AlarmSeverity.MAJOR: "🟠",
    AlarmSeverity.MINOR: "🟡",
    AlarmSeverity.WARNING: "🔵",
    AlarmSeverity.INDETERMINATE: "⚪",
}


class RateLimited(Exception):
    """This tenant already had its quota this minute; the next tick will do."""


def dispatch(now: datetime | None = None) -> dict:
    now = now or timezone.now()
    channel = TelegramChannel()
    stats = {"tenants": 0, "raised": 0, "cleared": 0, "failed": 0}

    for tenant in Tenant.objects.all():
        settings_data = notification_settings(tenant)
        if not channel.is_configured(settings_data):
            continue

        raised = list(pending_raised(tenant.id, settings_data, now))
        cleared = list(pending_cleared(tenant.id))
        if not raised and not cleared:
            continue

        stats["tenants"] += 1

        try:
            send(channel, tenant, settings_data, raised, cleared)
        except RateLimited:
            logger.info("Telegram rate limit reached for tenant %s; deferring to the next tick", tenant.id)
            continue
        except TelegramNotConfigured:
            # No bot token at all: nothing to retry, and every tenant would hit
            # the same wall.
            logger.info("Telegram notifications skipped: TELEGRAM_BOT_TOKEN is not set")
            return stats
        except TelegramAPIError as exc:
            stats["failed"] += 1
            if exc.is_permanent:
                record_error(tenant, exc.description)
                logger.warning("Telegram rejected tenant %s permanently: %s", tenant.id, exc.description)
            else:
                logger.warning("Telegram delivery to tenant %s failed: %s", tenant.id, exc.description)
            continue

        mark_sent([alarm.id for alarm in raised], [alarm.id for alarm in cleared], now)
        stats["raised"] += len(raised)
        stats["cleared"] += len(cleared)

    return stats


def pending_raised(tenant_id, settings_data: dict, now: datetime):
    cutoff = now - timedelta(seconds=int(settings_data.get("notify_delay_sec") or 0))
    return (
        Alarm.objects.filter(
            tenant_id=tenant_id,
            cleared=False,
            notified_at__isnull=True,
            start_ts__lte=cutoff,
            severity__in=allowed_severities(settings_data.get("min_severity")),
        )
        .select_related("originator", "room")
        .order_by("start_ts")
    )


def pending_cleared(tenant_id):
    # Only alarms whose raise was announced: no "resolved" message for an
    # incident nobody was told about.
    return (
        Alarm.objects.filter(
            tenant_id=tenant_id,
            cleared=True,
            notified_at__isnull=False,
            notified_clear_at__isnull=True,
        )
        .select_related("originator", "room")
        .order_by("clear_ts")
    )


def send(channel, tenant, settings_data: dict, raised: list[Alarm], cleared: list[Alarm]) -> None:
    if not take_token(tenant.id):
        raise RateLimited()

    channel.send(settings_data, build_message(tenant, raised, cleared))


def take_token(tenant_id) -> bool:
    cache = caches["default"]
    key = f"alarms:rate:{tenant_id}"
    try:
        if cache.add(key, 1, timeout=60):
            return True
        return cache.incr(key) <= RATE_LIMIT_PER_MINUTE
    except Exception:
        # A Redis hiccup must not stop alarms from going out.
        logger.warning("Alarm rate limiter unavailable for tenant %s", tenant_id, exc_info=True)
        return True


def build_message(tenant, raised: list[Alarm], cleared: list[Alarm]) -> str:
    offset = timezone_offset(tenant)
    parts = [f"<b>{html.escape(tenant.title or 'GRMS')}</b>"]

    if raised:
        parts.append("")
        parts.append(f"<b>Новые аварии ({len(raised)})</b>")
        parts.extend(alarm_lines(raised, offset, raised=True))

    if cleared:
        parts.append("")
        parts.append(f"<b>Снятые аварии ({len(cleared)})</b>")
        parts.extend(alarm_lines(cleared, offset, raised=False))

    return "\n".join(parts)


def alarm_lines(alarms: list[Alarm], offset: int, raised: bool) -> list[str]:
    lines = []
    for alarm in alarms[:MAX_LINES]:
        icon = SEVERITY_ICONS.get(alarm.severity, "⚪")
        moment = alarm.start_ts if raised else (alarm.clear_ts or alarm.end_ts)
        message = (alarm.details or {}).get("message") or alarm.alarm_type
        where = f" · {html.escape(str(alarm.room.number))}" if alarm.room_id else ""
        lines.append(f"{icon} {format_time(moment, offset)}{where} — {html.escape(str(message))}")

    if len(alarms) > MAX_LINES:
        lines.append(f"… и ещё {len(alarms) - MAX_LINES}")

    return lines


def timezone_offset(tenant) -> int:
    """``general_settings.timezone`` is a whole-hour offset in this project."""
    info = tenant.additional_info if isinstance(tenant.additional_info, dict) else {}
    try:
        return int((info.get("general_settings") or {}).get("timezone") or 0)
    except (TypeError, ValueError):
        return 0


def format_time(moment: datetime | None, offset: int) -> str:
    if moment is None:
        return "—"
    return (moment + timedelta(hours=offset)).strftime("%d.%m %H:%M")


def mark_sent(raised_ids: list, cleared_ids: list, now: datetime) -> None:
    if raised_ids:
        Alarm.objects.filter(id__in=raised_ids).update(notified_at=now)
    if cleared_ids:
        Alarm.objects.filter(id__in=cleared_ids).update(notified_clear_at=now)


def record_error(tenant, description: str) -> None:
    additional_info = tenant.additional_info if isinstance(tenant.additional_info, dict) else {}
    stored = additional_info.get(SETTINGS_KEY) or {}
    stored["telegram_last_error"] = description[:255]
    additional_info[SETTINGS_KEY] = stored
    tenant.additional_info = additional_info
    tenant.save(update_fields=["additional_info"])
