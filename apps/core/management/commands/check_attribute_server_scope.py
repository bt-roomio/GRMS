import time

from django.core.management.base import BaseCommand

from shuttle.models import AttributeKv


class Command(BaseCommand):
    help = "Checking Attributes SERVER_SCOPE"

    def handle(self, *args, **options):
        while True:
            print("Checking Attributes SERVER_SCOPE", int(time.time()))
            check_attribute_server_scope()
            time.sleep(10)


def check_attribute_server_scope():
    attribute_kv = AttributeKv.objects.filter(
        attribute_key="active", attribute_type=AttributeKv.SERVER_SCOPE, bool_v=True
    )

    for attr_active in attribute_kv:
        attr = AttributeKv.objects.get(entity_id=attr_active.entity, attribute_key="lastActivityTime")
        if attr.long_v <= int(time.time()) - 30:
            attr_active.bool_v = False
            attr_active.save()
