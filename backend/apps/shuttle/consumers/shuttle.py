import json
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder


from shuttle.models import TsKv
from shuttle.serializers.ts_kv import TsKvSerializer


class ShuttleConsumer(JsonWebsocketConsumer):
    def receive_json(self, content, **kwargs):
        user = self.scope["user"]
        if content.get("type") == "ENTITY_DATA":
            if not user.is_anonymous:
                instance = TsKv.objects.all()
                serializer = TsKvSerializer(instance, many=True).data
                devices = json.dumps(serializer, cls=DjangoJSONEncoder)
                self.send_json({"data": devices})
