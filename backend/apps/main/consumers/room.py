from channels.generic.websocket import JsonWebsocketConsumer

from main.models import Room


class RoomConsumer(JsonWebsocketConsumer):
    def receive_json(self, content, **kwargs):
        user = self.scope["user"]
        room = Room.objects.all()
        print(room)
