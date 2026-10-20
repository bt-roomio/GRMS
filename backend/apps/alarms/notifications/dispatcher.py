"""
Periodic notification dispatcher.

Driven entirely by the ``Alarm`` table — no watermark, no queue — so running it
twice in a row is a no-op the second time. Grouping one message per tenant and
channel is what keeps a gateway outage from becoming forty messages, and the
``notify_delay_sec`` window is what keeps a flapping link quiet.

Each channel target keeps its own ``AlarmNotification`` rows, so targets
deliver independently: a refused mailbox never delays Telegram, a Telegram
retry never sends the email twice, and a WhatsApp number that timed out is
retried alone without paying for the numbers that already got it.
"""

import logging
import time
from collections.abc import Iterable
from datetime import datetime, timedelta

from django.core.cache import caches
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from alarms.channels.base import ChannelNotConfigured, DeliveryError, NotificationChannel
from alarms.channels.registry import default_channels
from alarms.models import Alarm, AlarmNotification
from alarms.notifications.settings import (
    CHANNELS_KEY,
    SETTINGS_KEY,
    allowed_severities,
    channel_blocks,
    notification_settings,
    stored_settings,
)
from main.models import Tenant

logger = logging.getLogger(__name__)

# Telegram allows roughly 20 messages a minute to one chat; stay well under it.
# Applied per channel, so it equally keeps a mailbox from being flooded.
RATE_LIMIT_PER_MINUTE = 10

# Below the Celery soft time limit (300 s, ``config/celery.py``) with room for
# one slow send: stopping between targets is clean, being killed mid-target is
# not.
TIME_BUDGET_SEC = 240


class RateLimited(Exception):
    """This tenant already had its quota this minute; the next tick will do."""


def dispatch(
    now: datetime | None = None,
    channels: Iterable[NotificationChannel] | None = None,
    budget_sec: float = TIME_BUDGET_SEC,
) -> dict:
    now = now or timezone.now()
    channels = list(channels) if channels is not None else default_channels()
    stats = {"tenants": 0, "raised": 0, "cleared": 0, "failed": 0, "out_of_time": False}
    deadline = time.monotonic() + budget_sec
    # Channels the installation cannot use this tick (no bot token, no SMTP
    # sender): every remaining tenant would hit the same wall.
    unavailable: set[str] = set()

    for tenant in Tenant.objects.all():
        settings_data = notification_settings(tenant)
        touched = False

        for channel in channels:
            config = settings_data[CHANNELS_KEY].get(channel.name) or {}
            if channel.name in unavailable or not channel.is_configured(config):
                continue

            # Permanent refusals of this channel's targets, recorded together
            # so one bad number does not hide another.
            refusals: list[str] = []

            for key, target_config in channel.targets(config):
                raised = list(pending_raised(key, tenant.id, settings_data, now))
                cleared = list(pending_cleared(key, tenant.id))
                if not raised and not cleared:
                    continue

                touched = True

                if time.monotonic() > deadline:
                    # Leave the rest to the next tick rather than be killed by
                    # the soft time limit between a send and its mark_sent.
                    stats["out_of_time"] = True
                    logger.warning("Alarm notifications ran out of time; the rest goes out on the next tick")
                    return stats

                try:
                    send(channel, key, tenant, target_config, raised, cleared)
                except RateLimited:
                    logger.info("%s rate limit reached for tenant %s; deferring to the next tick", key, tenant.id)
                    continue
                except ChannelNotConfigured as exc:
                    unavailable.add(channel.name)
                    logger.info("%s notifications skipped: %s", channel.name, exc)
                    break
                except DeliveryError as exc:
                    stats["failed"] += 1
                    if exc.is_permanent:
                        refusals.append(exc.description)
                        logger.warning("%s rejected tenant %s permanently: %s", key, tenant.id, exc.description)
                    else:
                        logger.warning("%s delivery to tenant %s failed: %s", key, tenant.id, exc.description)
                    if exc.stop_channel:
                        break
                    continue

                # Right after each send: a target that went out is never
                # repeated, whatever happens to the next one.
                mark_sent(key, [alarm.id for alarm in raised], [alarm.id for alarm in cleared], now)
                stats["raised"] += len(raised)
                stats["cleared"] += len(cleared)

            if refusals:
                record_error(tenant, channel.name, "; ".join(refusals))

        if touched:
            stats["tenants"] += 1

    return stats


def pending_raised(key: str, tenant_id, settings_data: dict, now: datetime):
    cutoff = now - timedelta(seconds=int(settings_data.get("notify_delay_sec") or 0))
    return (
        Alarm.objects.filter(
            tenant_id=tenant_id,
            cleared=False,
            start_ts__lte=cutoff,
            severity__in=allowed_severities(settings_data.get("min_severity")),
        )
        .exclude(Exists(AlarmNotification.objects.filter(alarm=OuterRef("pk"), channel=key)))
        .select_related("originator", "room")
        .order_by("start_ts")
    )


def pending_cleared(key: str, tenant_id):
    # Only alarms whose raise this channel announced: no "resolved" message
    # for an incident nobody was told about.
    return (
        Alarm.objects.filter(
            Exists(AlarmNotification.objects.filter(alarm=OuterRef("pk"), channel=key, cleared_at=None)),
            tenant_id=tenant_id,
            cleared=True,
        )
        .select_related("originator", "room")
        .order_by("clear_ts")
    )


def send(channel: NotificationChannel, key: str, tenant, config: dict, raised: list[Alarm], cleared: list[Alarm]):
    if not take_token(key, tenant.id):
        raise RateLimited()

    channel.send(tenant, config, raised, cleared)


def take_token(key: str, tenant_id) -> bool:
    cache = caches["default"]
    cache_key = f"alarms:rate:{key}:{tenant_id}"
    try:
        if cache.add(cache_key, 1, timeout=60):
            return True
        return cache.incr(cache_key) <= RATE_LIMIT_PER_MINUTE
    except Exception:
        # A Redis hiccup must not stop alarms from going out.
        logger.warning("Alarm rate limiter unavailable for tenant %s", tenant_id, exc_info=True)
        return True


def mark_sent(key: str, raised_ids: list, cleared_ids: list, now: datetime) -> None:
    if raised_ids:
        AlarmNotification.objects.bulk_create(
            [AlarmNotification(alarm_id=alarm_id, channel=key, raised_at=now) for alarm_id in raised_ids],
            # A concurrent tick may have got there first; one row is the point.
            ignore_conflicts=True,
        )
    if cleared_ids:
        AlarmNotification.objects.filter(alarm_id__in=cleared_ids, channel=key).update(cleared_at=now)


def record_error(tenant, channel_name: str, description: str) -> None:
    # Re-read under a lock instead of saving the copy loaded at the start of
    # the tick: a settings PUT in between (a hotel entering a new token) would
    # otherwise be overwritten by the stale one.
    with transaction.atomic():
        fresh = Tenant.objects.select_for_update().only("id", "additional_info").get(pk=tenant.pk)
        additional_info = fresh.additional_info if isinstance(fresh.additional_info, dict) else {}
        stored = stored_settings(fresh)
        channels = channel_blocks(stored)
        channels.setdefault(channel_name, {})["last_error"] = description[:255]
        stored[CHANNELS_KEY] = channels
        additional_info[SETTINGS_KEY] = stored
        fresh.additional_info = additional_info
        fresh.save(update_fields=["additional_info"])
