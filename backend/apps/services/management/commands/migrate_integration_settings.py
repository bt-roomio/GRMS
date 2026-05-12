from django.core.management.base import BaseCommand

from main.models import Tenant
from services.models import Integration, Integrator
from services.utils.const import FIAS, HOTEZA, MEWS

MEWS_INTEGRATOR_FIELDS = {"client_token"}  # → Integrator.client_id
MEWS_INTEGRATION_FIELDS = {"access_token"}  # → Integration.access_token
MEWS_ADDITIONAL_FIELDS = {"environment", "send_tasks", "roomio_access_control", "last_sync", "last_keycard_fetch"}

TYPE_MAP = {
    "hoteza": HOTEZA,
    "mews": MEWS,
    "fias": FIAS,
}


class Command(BaseCommand):
    help = "Migrate integration_settings from Tenant.additional_info to Integration model"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN ---"))

        tenants = Tenant.objects.exclude(additional_info=None)
        created_total = updated_total = skipped_total = 0

        for tenant in tenants:
            i_settings = (tenant.additional_info or {}).get("integration_settings", {})
            if not i_settings:
                continue

            for key, integration_type in TYPE_MAP.items():
                settings = i_settings.get(key)
                if not settings or not isinstance(settings, dict):
                    continue

                hotel_id = settings.get("hotel_id") or None
                enable = bool(settings.get("enable", False))

                if integration_type == MEWS:
                    client_id = settings.get("client_token") or None
                    access_token = settings.get("access_token") or None
                    additional_info = {k: v for k, v in settings.items() if k in MEWS_ADDITIONAL_FIELDS} or None
                else:
                    client_id = None
                    access_token = None
                    additional_info = None

                existing = Integration.objects.filter(
                    tenant=tenant, integrator__name=integration_type, is_active=True
                ).first()

                if existing:
                    changed = (
                        existing.hotel_id != hotel_id
                        or existing.enable != enable
                        or existing.access_token != access_token
                    )
                    if not changed:
                        self.stdout.write(f"  SKIP   [{tenant.title}] {key} — no changes")
                        skipped_total += 1
                        continue

                    self.stdout.write(f"  UPDATE [{tenant.title}] {key}")
                    if not dry_run:
                        existing.hotel_id = hotel_id
                        existing.enable = enable
                        existing.access_token = access_token
                        if additional_info:
                            existing.additional_info = {**(existing.additional_info or {}), **additional_info}
                        existing.save(update_fields=["hotel_id", "enable", "access_token", "additional_info"])
                    updated_total += 1
                else:
                    self.stdout.write(f"  CREATE [{tenant.title}] {key}")
                    if not dry_run:
                        integrator, _ = Integrator.objects.update_or_create(
                            name=integration_type, defaults={"client_id": client_id}
                        )
                        Integration.objects.create(
                            tenant=tenant,
                            integrator=integrator,
                            hotel_id=hotel_id,
                            enable=enable,
                            access_token=access_token,
                            additional_info=additional_info,
                        )
                    created_total += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone: created={created_total}, updated={updated_total}, skipped={skipped_total}")
        )
