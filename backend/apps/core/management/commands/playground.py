from django.core.management.base import BaseCommand

from shuttle.models import TsKvDictionary, TsKvLatest


class Command(BaseCommand):
    help = "Playground"

    def handle(self, **_):
        ts_dict, _ = TsKvDictionary.objects.get_or_create(key="test")
        if ts_dict.key:
            lt_key, _ = TsKvLatest.objects.update_or_create(
                entity_id="ab29dabe-7fda-4437-988e-a1e07d58b68b",
                key=ts_dict,
                defaults={"dbl_v": None, "str_v": None, "long_v": None, "json_v": None},
            )
            print(lt_key.get_value)
