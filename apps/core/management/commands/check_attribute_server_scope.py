import time

from django.core.management.base import BaseCommand
from django.db.models import Count

from shuttle.models import AttributeKv


class Command(BaseCommand):
    help = "Checking Attributes SERVER_SCOPE"

    def handle(self, *args, **options):
        while True:
            print("Checking Attributes SERVER_SCOPE", time.time())
            check_attribute_server_scope()
            time.sleep(30)


def check_attribute_server_scope():
    attribute_kv = (
        AttributeKv.objects.values("entity", "attribute_type", "attribute_key", "long_v", "bool_v")
        .filter(attribute_key="lastActivityTime", attribute_type=AttributeKv.SERVER_SCOPE)
        .annotate(count=Count("entity"))
    )
    for attr in attribute_kv:
        if attr.get("attribute_key") == "lastActivityTime" and (attr.get("long_v") or 0 <= int(time.time()) - 30):
            AttributeKv.objects.filter(
                entity=attr["entity"],
                attribute_key="active",
                attribute_type=AttributeKv.SERVER_SCOPE,
            ).update(bool_v=False)
