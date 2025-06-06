from django.core.management.base import BaseCommand
from django.db.models import F, Func, JSONField, OuterRef, Subquery
from django.db.models.functions import Coalesce

from main.models import Room, Tenant
from main.querysets.room import JSONBObjectAgg
from shuttle.models import AttributeKv


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        tenant = Tenant.objects.get(id="124ed4ee-c3f2-4936-a625-8103dd25c364")
        query = Room.objects.filter(active=True, tenant=tenant)

        tskv_grouped = (
            AttributeKv.objects.filter(
                entity__room=OuterRef("pk"), attribute_type__in=[AttributeKv.SERVER_SCOPE], attribute_key__in=["active"]
            )
            .values("entity__room")
            .annotate(
                mapped=JSONBObjectAgg(
                    "attribute_key",
                    Coalesce(
                        Func(F("str_v"), function="to_jsonb", output_field=JSONField()),
                        Func(F("long_v"), function="to_jsonb", output_field=JSONField()),
                        Func(F("bool_v"), function="to_jsonb", output_field=JSONField()),
                        F("json_v"),
                        Func(F("dbl_v"), function="to_jsonb", output_field=JSONField()),
                        output_field=JSONField(),
                    ),
                )
            )
            .values("mapped")
        )
        query = query.annotate(attribute_values=Subquery(tskv_grouped))
        print(query)
