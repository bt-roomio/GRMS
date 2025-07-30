from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        tenant_admins = Role.objects.filter(name__in=["TENANT_ADMIN", "SYS_ADMIN"])
        permissions = Permission.objects.all()
        for tenant_admin in tenant_admins:
            tenant_admin.permissions.clear()
            tenant_admin.permissions.add(*permissions)
