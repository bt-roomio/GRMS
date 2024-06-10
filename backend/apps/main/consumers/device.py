import json
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder


from main.models import Device
from main.serializers.device import DeviceSerializer


class DeviceConsumer(JsonWebsocketConsumer):
    def receive_json(self, content, **kwargs):
        user = self.scope["user"]
        if not user.is_anonymous:
            instance = Device.objects.all()
            serializer = DeviceSerializer(instance, many=True).data
            devices = json.dumps(serializer, cls=DjangoJSONEncoder)
            self.send_json({"data": devices})
