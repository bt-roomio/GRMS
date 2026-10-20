import re
from collections.abc import Callable
from typing import Any, ClassVar

from django.conf import settings

from alarms.channels.base import DeliveryError
from alarms.constants import SEVERITY_RANK
from alarms.notifications.message import alarm_lines, tenant_title, timezone_offset
from alarms.whatsapp.client import WhatsAppClient
from alarms.whatsapp.exceptions import WhatsAppAPIError, WhatsAppSenderRejected, WhatsAppUnavailable
from core.utils.secrets import SecretDecryptionError, decrypt

# Meta refuses template parameters with newlines, tabs or more than four
# consecutive spaces, and the whole body is capped at 1024 characters.
WHITESPACE = re.compile(r"\s+")
MAX_PARAM_LENGTH = 200
EMPTY_PARAM = "—"


class WhatsAppChannel:
    """
    One approved template per message, one message per recipient — the Cloud
    API has no broadcast. The template is a summary rather than the full list
    Telegram and email get, because a parameter cannot span lines::

        Объект «{{1}}»: обновление по авариям.
        Новых: {{2}}. Снятых: {{3}}.
        Главное: {{4}}
        Подробности в панели roomio.

    Its name and language are installation settings (``WA_ALARM_TEMPLATE``,
    ``WA_TEMPLATE_LANGUAGE``); each hotel gets a template of that name approved
    in its own WhatsApp Business Account.

    Sender: always the hotel's own number — ``phone_number_id`` and the
    ``access_token`` (stored encrypted) from its block. There is deliberately
    no installation number to fall back to: Meta bills the sending account, and
    a hotel must never send at roomio's expense. Every refusal therefore
    concerns one tenant and lands in its ``last_error``.

    Each number is its own target with its own ``AlarmNotification`` rows
    (``whatsapp:<number>``): a timeout retries that number alone, and a number
    added later catches up on the active alarms.
    """

    name: ClassVar[str] = "whatsapp"
    defaults: ClassVar[dict[str, Any]] = {
        "enabled": False,
        "recipients": [],
        "phone_number_id": "",
        # Fernet ciphertext; the settings API never returns it.
        "access_token": "",
        "last_error": None,
    }

    def __init__(self, client_factory: Callable[..., WhatsAppClient] = WhatsAppClient):
        self.client_factory = client_factory

    def is_configured(self, config: dict) -> bool:
        # Credentials are not part of it on purpose: enabled without them must
        # surface as last_error, not as silence.
        return bool(config.get("enabled") and config.get("recipients"))

    def targets(self, config: dict) -> list[tuple[str, dict]]:
        # One target per number: each message is a separate paid call, so a
        # number that failed is retried alone. "whatsapp:" + 15 digits fits
        # AlarmNotification.channel.
        return [(f"{self.name}:{phone}", {**config, "recipients": [phone]}) for phone in config["recipients"]]

    def client_for(self, config: dict) -> WhatsAppClient:
        phone_number_id = config.get("phone_number_id") or ""
        access_token = config.get("access_token") or ""
        if not phone_number_id or not access_token:
            raise DeliveryError(
                "phone_number_id and access_token of the hotel's own number are required",
                permanent=True,
                stop_channel=True,
            )

        try:
            token = decrypt(access_token)
        except SecretDecryptionError as exc:
            raise DeliveryError(
                "Stored access token cannot be decrypted; enter it again", permanent=True, stop_channel=True
            ) from exc

        try:
            return self.client_factory(token=token, phone_number_id=phone_number_id)
        except WhatsAppSenderRejected as exc:
            raise DeliveryError(str(exc), permanent=True, stop_channel=True) from exc

    def send(self, tenant, config: dict, raised: list, cleared: list) -> None:
        """
        Sends to every number in ``config["recipients"]`` and stops at the
        first failure. The dispatcher passes one number at a time (see
        ``targets``), so a failure never hides who already got the message.
        """
        params = build_params(tenant, raised, cleared)

        with self.client_for(config) as client:
            for phone in config["recipients"]:
                try:
                    client.send_template(phone, settings.WA_ALARM_TEMPLATE, settings.WA_TEMPLATE_LANGUAGE, params)
                except (WhatsAppAPIError, WhatsAppUnavailable) as exc:
                    raise DeliveryError(f"{phone}: {exc.description}", permanent=exc.is_permanent) from exc
                except WhatsAppSenderRejected as exc:
                    # The hotel's token or template: every other number would
                    # get the same answer, and only this tenant can fix it.
                    raise DeliveryError(str(exc), permanent=True, stop_channel=True) from exc


def build_params(tenant, raised: list, cleared: list) -> list[str]:
    return [
        clean(tenant_title(tenant)),
        str(len(raised)),
        str(len(cleared)),
        clean(headline(tenant, raised, cleared)),
    ]


def headline(tenant, raised: list, cleared: list) -> str:
    """The most severe new alarm, or the first cleared one when nothing is new."""
    is_raised = bool(raised)
    if raised:
        alarm = min(raised, key=lambda a: (SEVERITY_RANK.get(a.severity, len(SEVERITY_RANK)), a.start_ts))
    elif cleared:
        alarm = cleared[0]
    else:
        return EMPTY_PARAM

    line = alarm_lines([alarm], timezone_offset(tenant), raised=is_raised)[0]
    where = f" · {line.room}" if line.room else ""
    icon = line.icon if is_raised else "✅"
    return f"{icon} {line.time}{where} — {line.text}"


def clean(text: str) -> str:
    """Meta rejects the whole message over one bad parameter, empty ones included."""
    text = WHITESPACE.sub(" ", text).strip()
    if len(text) > MAX_PARAM_LENGTH:
        text = text[: MAX_PARAM_LENGTH - 1] + "…"
    return text or EMPTY_PARAM
