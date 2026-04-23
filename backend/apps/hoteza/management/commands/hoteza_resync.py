import logging
from datetime import datetime, timedelta

import requests
from django.core.management.base import BaseCommand, CommandError

from main.models import Tenant

logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class Command(BaseCommand):
    help = "Trigger resynchronization on Hoteza Cloud (protocol section 3.6)"

    def add_arguments(self, parser):
        parser.add_argument("--hoteza-url", type=str, required=True, help="Hoteza Cloud base URL (e.g. http://host)")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--hotel-id", type=str, help="Hotel ID in Hoteza Cloud")
        group.add_argument("--tenant-id", type=str, help="Tenant ID to look up hotel ID from integration settings")
        parser.add_argument(
            "--start", type=str, help=f"Start datetime ({DATETIME_FORMAT}), default: yesterday 00:00:00"
        )
        parser.add_argument("--end", type=str, help=f"End datetime ({DATETIME_FORMAT}), default: today 23:59:59")

    def handle(self, *args, **options):
        hotel_id = options["hotel_id"] or self._get_hotel_id_from_tenant(options["tenant_id"])

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_dt = options["start"] or (today - timedelta(days=1)).strftime(DATETIME_FORMAT)
        end_dt = options["end"] or today.replace(hour=23, minute=59, second=59).strftime(DATETIME_FORMAT)

        url = options["hoteza_url"].rstrip("/") + "/pmsconnect/resync"
        payload = {"hotelId": hotel_id, "startDateTime": start_dt, "endDateTime": end_dt}

        self.stdout.write(f"POST {url}  payload={payload}")

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise CommandError(f"Request failed: {e}")

        data = response.json()
        if data.get("result") == 0:
            self.stdout.write(self.style.SUCCESS("Resync successful"))
        else:
            raise CommandError(f"Resync failed: {data}")

    def _get_hotel_id_from_tenant(self, tenant_id: str) -> str:
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            raise CommandError(f"Tenant {tenant_id} not found")

        hotel_id = (tenant.additional_info or {}).get("integration_settings", {}).get("hoteza", {}).get("hotel_id")
        if not hotel_id:
            raise CommandError(f"Tenant {tenant_id} has no Hoteza hotel_id configured")

        self.stdout.write(f"Tenant: {tenant.title}, hotelId: {hotel_id}")
        return hotel_id
