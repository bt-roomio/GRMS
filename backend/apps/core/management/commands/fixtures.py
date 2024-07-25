from django.contrib.auth.models import Permission, Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Loads all fixtures"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command(
            "loaddata",
            "groups_permissions",
            "tenant_profile",
            "tenant",
            "users",
            "email_configuration",
            "groups_permissions",
            "device_profile",
            "customer",
            "room",
            "device",
            "device_credentials",
            "attribute_kv",
            "room_type",
            "widget_type",
            "dashboard",
            "ts_dictionary",
            "ts_kv",
            "ts_kv_latest",
        )

        # # # Giving all permissions for SYS_ADMIN
        perms = Permission.objects.select_related("content_type").all()
        group = Group.objects.filter(name="SYS_ADMIN").first()
        group.permissions.set(perms)
