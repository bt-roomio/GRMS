import json

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from users.models import Role


class Command(BaseCommand):
    help = "Reset ContentType & Permission IDs; reconnect existing UUID-based roles"

    def handle(self, *args, **options):
        self.stdout.write("🔄 Backing up data...")

        content_types = list(ContentType.objects.all().values())
        permissions = list(Permission.objects.all().values())

        role_permissions = {
            str(role.id): list(role.permissions.values_list("id", flat=True))
            for role in Role.objects.prefetch_related("permissions")
        }

        backup_data = {
            "content_types": content_types,
            "permissions": permissions,
            "role_permissions": role_permissions,
        }

        with open("backup_permission_reset_grms_2.json", "w") as f:
            json.dump(backup_data, f, indent=2)

        self.stdout.write("✅ Backup saved to 'backup_permission_reset.json'")

        self._truncate("auth_permission")
        self._truncate("django_content_type")
        self._truncate("users_roles_permissions")

        with transaction.atomic():
            new_ct_ids = {}
            for ct in content_types:
                old_id = ct.pop("id")
                new_ct = ContentType.objects.create(**ct)
                new_ct_ids[old_id] = new_ct.id

            new_perm_ids = {}
            for perm in permissions:
                old_id = perm.pop("id")
                perm["content_type_id"] = new_ct_ids[perm["content_type_id"]]
                new_perm = Permission.objects.create(**perm)
                new_perm_ids[old_id] = new_perm.id

            for role_id, perm_ids in role_permissions.items():
                try:
                    role = Role.objects.get(id=role_id)
                    new_perms = [new_perm_ids[pid] for pid in perm_ids if pid in new_perm_ids]
                    role.permissions.set(new_perms)
                except Role.DoesNotExist:
                    continue

        self.stdout.write(self.style.SUCCESS("🎉 Permissions and ContentTypes reset, Role links updated."))

    def _truncate(self, table):
        with connection.cursor() as cursor:
            self.stdout.write(f"🧹 Truncating {table}")
            cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')
