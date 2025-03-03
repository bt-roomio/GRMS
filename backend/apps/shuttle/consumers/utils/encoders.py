from uuid import UUID

from django.core.serializers.json import DjangoJSONEncoder


class UUIDEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, UUID):
            return str(o)
        return super().default(o)
