from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Loads all fixtures"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command(
            "loaddata",
            "roles_permissions",
            "tenant_profile",
            "tenant",
            "users",
            "email_configuration",
            "device_profile",
            "customer",
            "room",
            "device",
            "device_credentials",
            "attribute_kv",
            "room_type",
            "guest",
            "widget_type",
            "dashboard",
            "ts_dictionary",
            "ts_kv",
            "ts_kv_latest",
        )
