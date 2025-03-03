import time

from django.core.management.base import BaseCommand

from core.utils.get_time import get_mil_sec
from shuttle.models import AttributeKv, Relation


class Command(BaseCommand):
    help = "Checking Attributes SERVER_SCOPE"

    def handle(self, *args, **options):
        while True:
            print("Checking Attributes SERVER_SCOPE", get_mil_sec())
            active_attribute_server_scope()
            time.sleep(10)


def active_attribute_server_scope():
    attribute_kv = AttributeKv.objects.select_related("entity").filter(
        entity__additional_info__gateway=True, attribute_key="active"
    )
    check_activity_time(attribute_kv)


def check_activity_time(attribute_kv):
    for attr_active in attribute_kv:
        attr = AttributeKv.objects.get(entity_id=attr_active.entity, attribute_key="lastActivityTime")
        if attr.long_v < get_mil_sec() - 60000:
            attr_active.bool_v = False
            attr_active.save()
            print(f"Device id: {attr.entity_id}")

            if attr.entity.additional_info and attr.entity.additional_info.get("gateway"):
                relations = Relation.objects.filter(from_id=attr_active.entity_id)
                relation_devices = list(relations.values_list("to_id_id", flat=True))
                relation_attrs = AttributeKv.objects.filter(
                    entity_id__in=relation_devices, attribute_key="active", bool_v=True
                )
                for relation_attr in relation_attrs:
                    print(f"Relation: {relation_attr.entity_id}")
                    relation_attr.bool_v = False
                    relation_attr.save()
