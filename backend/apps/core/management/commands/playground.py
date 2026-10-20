from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from alarms.channels.base import DeliveryError
from alarms.channels.whatsapp import WhatsAppChannel, build_params
from alarms.models import Alarm
from alarms.notifications.settings import CHANNELS_KEY, notification_settings
from alarms.whatsapp.exceptions import WhatsAppError
from alarms.whatsapp.phone import normalize_phone
from main.models import Tenant


class Command(BaseCommand):
    help = (
        "Send a test WhatsApp message from a tenant's own number. By default the pre-approved "
        "hello_world template; with --alarm, a simulated alarm summary through WhatsAppChannel."
    )

    def add_arguments(self, parser):
        parser.add_argument("to", help="Recipient phone in international format, e.g. +998901234567")
        parser.add_argument("--alarm", action="store_true", help="Send WA_ALARM_TEMPLATE with fake alarms")
        parser.add_argument("--tenant", help="Tenant whose WhatsApp settings to send with (default: the first one)")
        parser.add_argument("--dry-run", action="store_true", help="Only print what would be sent")

    def handle(self, to, alarm, tenant, dry_run, **_):
        # The same rules as the settings API, so a number that works here is
        # one the panel accepts.
        phone = normalize_phone(to)
        if phone is None:
            raise CommandError(f"{to!r} is not a phone number in international format")

        try:
            tenant = Tenant.objects.get(pk=tenant) if tenant else Tenant.objects.order_by("created_at").first()
        except (Tenant.DoesNotExist, ValidationError) as exc:
            raise CommandError(f"Tenant {tenant!r} not found") from exc
        if tenant is None:
            raise CommandError("No tenant found")

        # The tenant's sender; recipients replaced by the argument.
        config = {**notification_settings(tenant)[CHANNELS_KEY]["whatsapp"], "enabled": True, "recipients": [phone]}
        self.stdout.write(f"Tenant {tenant.title} ({tenant.id}), sender {config['phone_number_id'] or '—'}")

        try:
            if alarm:
                self.send_alarm(tenant, config, phone, dry_run)
            else:
                self.send_hello_world(config, phone, dry_run)
        except (DeliveryError, WhatsAppError) as exc:
            raise CommandError(str(exc)) from exc

    def send_hello_world(self, config: dict, phone: str, dry_run: bool):
        self.stdout.write(f"hello_world (en_US) -> {phone}")
        if dry_run:
            return

        with WhatsAppChannel().client_for(config) as client:
            wamid = client.send_template(phone, "hello_world", "en_US", [])
        self.stdout.write(self.style.SUCCESS(f"Accepted by Meta, wamid={wamid}"))

    def send_alarm(self, tenant, config: dict, phone: str, dry_run: bool):
        raised, cleared = fake_alarms(tenant)

        self.stdout.write(f"{settings.WA_ALARM_TEMPLATE} ({settings.WA_TEMPLATE_LANGUAGE}) -> {phone}")
        for number, value in enumerate(build_params(tenant, raised, cleared), start=1):
            self.stdout.write(f"  {{{{{number}}}}} = {value}")
        if dry_run:
            return

        WhatsAppChannel().send(tenant, config, raised, cleared)
        self.stdout.write(self.style.SUCCESS("Accepted by Meta; delivery status arrives on the hotel's webhook"))


def fake_alarms(tenant) -> tuple[list[Alarm], list[Alarm]]:
    """Unsaved alarms: nothing lands in the journal and the dispatcher never sees them."""
    now = timezone.now()

    def alarm(severity: str, alarm_type: str, message: str, minutes_ago: int, cleared: bool = False) -> Alarm:
        start = now - timedelta(minutes=minutes_ago)
        return Alarm(
            tenant=tenant,
            alarm_type=alarm_type,
            severity=severity,
            start_ts=start,
            end_ts=start,
            cleared=cleared,
            clear_ts=now if cleared else None,
            details={"message": message},
        )

    raised = [
        alarm("MINOR", "High Temperature", "Температура 31° в номере 512", 12),
        alarm("CRITICAL", "Gateway Offline", "Шлюз GW-3 не на связи", 7),
    ]
    cleared = [alarm("MAJOR", "Device Offline", "Устройство DHT11 не на связи", 40, cleared=True)]
    return raised, cleared
