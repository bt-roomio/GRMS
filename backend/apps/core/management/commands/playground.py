import json

from django.core.management.base import BaseCommand
from shuttle.models import TsKv


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        with open("ts_kv.json", "r") as f:
            data = json.load(f)
            for item in data:
                TsKv.objects.create(**item)
