import html
import smtplib
from typing import Any, ClassVar

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from alarms.channels.base import ChannelNotConfigured, DeliveryError
from alarms.notifications.message import (
    CLEARED_TITLE,
    RAISED_TITLE,
    AlarmLine,
    alarm_lines,
    overflow,
    tenant_title,
    timezone_offset,
)

SEVERITY_COLORS = {
    "CRITICAL": "#d32f2f",
    "MAJOR": "#f57c00",
    "MINOR": "#fbc02d",
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

    def send(self, tenant, config: dict, raised: list, cleared: list) -> None:
        sender = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        if not settings.EMAIL_HOST or not sender:
            raise ChannelNotConfigured("EMAIL_HOST and DEFAULT_FROM_EMAIL must be set to send alarm notifications")

        message = EmailMultiAlternatives(
            subject=build_subject(tenant, raised, cleared),
            body=build_text(tenant, raised, cleared),
            from_email=sender,
            to=list(config["recipients"]),
            connection=get_connection(fail_silently=False),
        )
        message.attach_alternative(build_html(tenant, raised, cleared), "text/html")

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
        counts.append(f"новых {len(raised)}")
    if cleared:
        counts.append(f"снятых {len(cleared)}")
    return f"{tenant_title(tenant)}: аварии — {', '.join(counts)}"


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


def build_html(tenant, raised: list, cleared: list) -> str:
    parts = [f"<h2 style='margin:0 0 12px'>{html.escape(tenant_title(tenant))}</h2>"]

    for title, lines, more in sections(tenant, raised, cleared):
        parts.append(f"<h3 style='margin:16px 0 8px'>{html.escape(title)}</h3>")
        parts.append("<table cellpadding='4' cellspacing='0' style='border-collapse:collapse'>")
        parts.extend(html_row(line) for line in lines)
        parts.append("</table>")
        if more:
            parts.append(f"<p style='color:#757575'>{html.escape(more)}</p>")

    return "<div style='font-family:Arial,sans-serif;font-size:14px'>" + "".join(parts) + "</div>"


def html_row(line: AlarmLine) -> str:
    color = SEVERITY_COLORS.get(line.severity, "#9e9e9e")
    return (
        "<tr>"
        f"<td style='color:{color};font-weight:bold;white-space:nowrap'>{html.escape(line.severity)}</td>"
        f"<td style='white-space:nowrap'>{html.escape(line.time)}</td>"
        f"<td style='white-space:nowrap'>{html.escape(line.room or '')}</td>"
        f"<td>{html.escape(line.text)}</td>"
        "</tr>"
    )
