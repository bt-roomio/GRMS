import smtplib
from dataclasses import asdict
from typing import Any, ClassVar

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

from alarms.channels.base import ChannelNotConfigured, DeliveryError
from alarms.notifications.message import (
    CLEARED_TITLE,
    RAISED_TITLE,
    alarm_lines,
    overflow,
    tenant_title,
    timezone_offset,
)

SEVERITY_COLORS = {
    "CRITICAL": "#d32f2f",
    "MAJOR": "#f57c00",
    "MINOR": "#e6a700",
    "WARNING": "#1976d2",
    "INDETERMINATE": "#9e9e9e",
}


class EmailChannel:
    """
    Goes through the project's own SMTP settings (``EMAIL_*``) — the same
    server that sends password resets, so there is nothing new to configure at
    the installation level; a tenant only lists its recipients.
    """

    name: ClassVar[str] = "email"
    defaults: ClassVar[dict[str, Any]] = {"enabled": False, "recipients": [], "last_error": None}

    def is_configured(self, config: dict) -> bool:
        return bool(config.get("enabled") and config.get("recipients"))

    def targets(self, config: dict) -> list[tuple[str, dict]]:
        # One message for the whole block.
        return [(self.name, config)]

    def send(self, tenant, config: dict, raised: list, cleared: list) -> None:
        sender = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        if not settings.EMAIL_HOST or not sender:
            raise ChannelNotConfigured("EMAIL_HOST and DEFAULT_FROM_EMAIL must be set to send alarm notifications")

        subject = build_subject(tenant, raised, cleared)
        message = EmailMultiAlternatives(
            subject=subject,
            body=build_text(tenant, raised, cleared),
            from_email=sender,
            to=list(config["recipients"]),
            connection=get_connection(fail_silently=False),
        )
        message.attach_alternative(build_html(tenant, subject, raised, cleared), "text/html")

        try:
            message.send()
        except smtplib.SMTPRecipientsRefused as exc:
            # Raised only when every address was refused: the list is wrong,
            # which only the tenant can fix.
            refused = ", ".join(sorted(exc.recipients))
            raise DeliveryError(f"SMTP refused all recipients: {refused}", permanent=True) from exc
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPSenderRefused) as exc:
            # The installation's mailbox, not the tenant's settings.
            raise ChannelNotConfigured(f"SMTP rejected the sender: {exc}") from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise DeliveryError(f"SMTP delivery failed: {exc}") from exc


def build_subject(tenant, raised: list, cleared: list) -> str:
    counts = []
    if raised:
        counts.append(f"{len(raised)} new")
    if cleared:
        counts.append(f"{len(cleared)} cleared")
    return f"{tenant_title(tenant)}: alarms — {', '.join(counts)}"


def sections(tenant, raised: list, cleared: list):
    offset = timezone_offset(tenant)
    for title, alarms, is_raised in ((RAISED_TITLE, raised, True), (CLEARED_TITLE, cleared, False)):
        if alarms:
            yield f"{title} ({len(alarms)})", alarm_lines(alarms, offset, raised=is_raised), overflow(alarms)


def build_text(tenant, raised: list, cleared: list) -> str:
    parts = [tenant_title(tenant)]

    for title, lines, more in sections(tenant, raised, cleared):
        parts.append("")
        parts.append(title)
        for line in lines:
            where = f" · {line.room}" if line.room else ""
            parts.append(f"{line.icon} {line.time}{where} — {line.text}")
        if more:
            parts.append(more)

    return "\n".join(parts)


def build_html(tenant, subject: str, raised: list, cleared: list) -> str:
    """Same layout as the password reset email (``core/templates/base_email.html``)."""
    sections_data = [
        {
            "title": title,
            "rows": [{**asdict(line), "color": SEVERITY_COLORS.get(line.severity, "#9e9e9e")} for line in lines],
            "more": more,
        }
        for title, lines, more in sections(tenant, raised, cleared)
    ]
    panel_url = (settings.FRONTEND_DOMAIN or "").rstrip("/")
    return render_to_string(
        "alarm_email.html",
        {"subject": subject, "title": tenant_title(tenant), "sections": sections_data, "panel_url": panel_url},
    )
