from django.core.management.base import BaseCommand

from shuttle.models import AttributeKv


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        obj = AttributeKv.objects.get(
            attribute_key="active",
            attribute_type=AttributeKv.SERVER_SCOPE,
            entity_id="47aef21b-6cc9-4ec5-8573-1a6f491940c0",
        )
        obj.bool_v = True
        obj.save()
