"""
Per-tenant notification settings, kept in ``Tenant.additional_info``.

Same singleton-resource shape as ``alarm_settings`` and ``general_settings``:
no table, edited through one PUT. Thresholds are deliberately not here — those
live in the rules, where TB keeps them.

Shape::

    {
        "notify_delay_sec": 300,
        "min_severity": "MINOR",
        "channels": {"telegram": {...}, "email": {...}},
    }

The top level is shared by every channel; each channel owns its block.
"""

from typing import Any

from alarms.channels.registry import CHANNELS
from alarms.constants import SEVERITY_RANK, AlarmSeverity

SETTINGS_KEY = "notification_settings"
CHANNELS_KEY = "channels"

DEFAULTS: dict[str, Any] = {
    # Alarms younger than this are not sent yet: an outage that clears inside
    # the window never produces a message, which is the whole flapping guard.
    "notify_delay_sec": 300,
    "min_severity": AlarmSeverity.MINOR.value,
}


def stored_settings(tenant) -> dict[str, Any]:
    """The raw block as saved, without defaults."""
    info = tenant.additional_info if isinstance(tenant.additional_info, dict) else {}
    stored = info.get(SETTINGS_KEY)
    return stored if isinstance(stored, dict) else {}


def channel_blocks(stored: dict[str, Any]) -> dict[str, Any]:
    blocks = stored.get(CHANNELS_KEY)
    return blocks if isinstance(blocks, dict) else {}


def notification_settings(tenant) -> dict[str, Any]:
    """The full settings, every registered channel present with its defaults."""
    stored = stored_settings(tenant)
    stored_channels = channel_blocks(stored)

    channels = {}
    for channel in CHANNELS:
        block = stored_channels.get(channel.name)
        channels[channel.name] = {**channel.defaults, **(block if isinstance(block, dict) else {})}

    return {**DEFAULTS, **{key: value for key, value in stored.items() if key in DEFAULTS}, CHANNELS_KEY: channels}


def allowed_severities(min_severity: str | None) -> list[str]:
    """Severities at or above the tenant's floor, CRITICAL always included."""
    limit = SEVERITY_RANK.get(min_severity, SEVERITY_RANK[AlarmSeverity.INDETERMINATE])
    return [severity.value for severity, rank in SEVERITY_RANK.items() if rank <= limit]
