from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from main.models import Tenant
from main.tasks import provision_nodered_task


class Command(BaseCommand):
    help = "Queue (re-)provisioning of a tenant's Node-RED: DNS record, env file and container"

    def add_arguments(self, parser):
        parser.add_argument("tenant", help="Tenant id or title")

    def handle(self, *args, **options):
        value = options["tenant"]
        lookup = Q(title__iexact=value)
        try:
            lookup |= Q(pk=UUID(value))
        except ValueError:
            pass  # not a uuid, match by title only

        tenant = Tenant.objects.filter(lookup).first()
        if not tenant:
            raise CommandError(f"Tenant '{value}' not found")

        # Queued rather than run here: only celery-low has the Docker socket and deploy/ mounted.
        provision_nodered_task.delay(str(tenant.id))
        self.stdout.write(
            self.style.SUCCESS(
                f"Queued Node-RED provisioning for '{tenant.title}'. "
                'Progress: tenant.additional_info["nodered"] or Flower.'
            )
        )
