"""
Per-tenant notification settings, kept in ``Tenant.additional_info``.

Same singleton-resource shape as ``alarm_settings`` and ``general_settings``:
no table, no migration, edited through one PUT. Thresholds are deliberately not
here — those live in the rules, where TB keeps them.
"""

from typing import Any

from alarms.constants import SEVERITY_RANK, AlarmSeverity

SETTINGS_KEY = "notification_settings"

DEFAULTS: dict[str, Any] = {
    "telegram_enabled": False,
    "telegram_chat_id": "",
    # Written by the dispatcher when Telegram rejects the chat for good, so the
    # settings screen can say why nothing arrives.
    "telegram_last_error": None,
    # Alarms younger than this are not sent yet: an outage that clears inside
    # the window never produces a message, which is the whole flapping guard.
    "notify_delay_sec": 300,
    "min_severity": AlarmSeverity.MINOR.value,
}


def notification_settings(tenant) -> dict[str, Any]:
    info = tenant.additional_info if isinstance(tenant.additional_info, dict) else {}
    stored = info.get(SETTINGS_KEY)
    return {**DEFAULTS, **(stored if isinstance(stored, dict) else {})}


def allowed_severities(min_severity: str | None) -> list[str]:
    """Severities at or above the tenant's floor, CRITICAL always included."""
    limit = SEVERITY_RANK.get(min_severity, SEVERITY_RANK[AlarmSeverity.INDETERMINATE])
    return [severity.value for severity, rank in SEVERITY_RANK.items() if rank <= limit]
