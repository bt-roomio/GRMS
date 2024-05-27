from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction


class Command(BaseCommand):
    help = "Loads all fixtures"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command(
            "loaddata",
            "tenant_profile",
            "tenant",
            "users",
            "email_configuration",
            "groups_permissions",
            "device_profile",
            "customer",
            "device",
            "room",
            "attribute_kv",
            "room_type",
        )
