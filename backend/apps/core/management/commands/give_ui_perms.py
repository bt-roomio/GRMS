from django.core.management.base import BaseCommand

from core.utils.constants import UI_PERMISSIONS
from users.models import Role


class Command(BaseCommand):
    help = "Assign UI permissions to all TENANT_ADMIN roles"

    def handle(self, **_):
        roles = Role.objects.filter(name="TENANT_ADMIN")
        updated = 0

        for role in roles:
            if not isinstance(role.additional_info, dict):
                role.additional_info = {}
            role.additional_info["ui_permissions"] = UI_PERMISSIONS
            updated += 1

        Role.objects.bulk_update(roles, ["additional_info"])
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} TENANT_ADMIN role(s)"))
