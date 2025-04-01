import json
from uuid import UUID

from djangochannelsrestframework.generics import GenericAsyncAPIConsumer


class UUIDEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, UUID):
            return o.hex
        return json.JSONEncoder.default(self, o)


class BaseGenericAsyncAPIConsumer(GenericAsyncAPIConsumer):
    pagination_class = None

    @classmethod
    async def encode_json(cls, content):
        return json.dumps(content, cls=UUIDEncoder)

    def pagination(self, queryset, page=1, size=15):
        page = page or 1
        offset = (page - 1) * size
        limit = offset + size
        queryset = queryset[offset:limit]
        return queryset
