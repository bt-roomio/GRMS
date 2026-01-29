from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        ...
