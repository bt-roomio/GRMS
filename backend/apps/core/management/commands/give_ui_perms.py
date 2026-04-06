from django.core.management.base import BaseCommand

from core.utils.constants import UI_PERMISSIONS
from users.models import User


class Command(BaseCommand):
    help = "Playground"

    def handle(self, **_):
        users = User.objects.filter(roles__name="TENANT_ADMIN")
        print(f"Users: {users}, len: {users.count()}")
        for user in users:
            print(f"User: {user}, Tenant: {user.tenant}")
            for role in user.roles.filter(name="TENANT_ADMIN"):
                print(f"User: {user}, role: {role.name}")
                if role and isinstance(role.additional_info, dict):
                    role.additional_info["ui_permissions"] = UI_PERMISSIONS
                    role.save()
                    print(f"Role: {role}, perms: {len(role.additional_info['ui_permissions'])}")
