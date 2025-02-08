from channels.db import database_sync_to_async

from users.models import User


@database_sync_to_async
def get_user(data):
    return User.objects.select_related("tenant").get(id=data["user_id"])
