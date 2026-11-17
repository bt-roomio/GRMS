from django.core.management.base import BaseCommand

from users.models import Role


class Command(BaseCommand):
    help = "Assign all UI permissions to all TENANT_ADMIN and SYS_ADMIN roles"

    def handle(self, **_):
        updated = Role.objects.admins().grant_all_ui_permissions()
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} admin role(s)"))
