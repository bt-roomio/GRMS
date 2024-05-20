from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Playground"

    @transaction.atomic
    def handle(self, *args, **options):
        pass
