from django.utils import timezone

from drf_yasg.utils import APIView
from rest_framework.views import Response

from core.utils.get_time import get_mil_sec
from shuttle.models import TsKv, TsKvDictionary, TsKvLatest


class TempAPIChangeTsKvLatest(APIView):
    def post(self, request, entity_id):
        data = request.data
        if not data:
            return Response({"message": "Empty data"}, 400)
        key_name, _ = TsKvDictionary.objects.get_or_create(key=data.pop("key"))
        TsKvLatest.objects.update_or_create(entity_id=entity_id, key=key_name, defaults={**data, "ts": get_mil_sec()})
        TsKv.objects.update_or_create(entity_id=entity_id, key=key_name, ts=timezone.now(), defaults={**data})
        return Response({"message": "Success"})
