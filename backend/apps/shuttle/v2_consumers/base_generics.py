import json
from uuid import UUID

from asgiref.sync import sync_to_async
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer

from users.models import User


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

    def get_user(self):
        return User.objects.filter(pk=self.scope["user"].id).values().first()

    def get_data_paginated(self, query_params, **kwargs):
        queryset = self.get_queryset(query_params=query_params)
        count = queryset.count()
        queryset = self.pagination(queryset, query_params.get("page", 1), query_params.get("size", 15))
        serializer = self.get_serializer(instance=queryset, many=True, action_kwargs=kwargs)
        return {"results": serializer.data, "count": count}

    async def send_list_paginated(self, action, query_params, request_id, **kwargs):
        data = await sync_to_async(self.get_data_paginated)(query_params=query_params, **kwargs)
        await self.reply(data=data, action=action, request_id=request_id)

    def get_data(self, **kwargs):
        queryset = self.get_queryset(query_params=kwargs.get("query_params"))
        serializer = self.get_serializer(instance=queryset, many=True, action_kwargs=kwargs)
        return serializer.data

    async def send_list(self, action, query_params, request_id, **kwargs):
        data = await sync_to_async(self.get_data)(query_params=query_params, **kwargs)
        await self.reply(data=data, action=action, request_id=request_id)

    def pagination(self, queryset, page, size=15):

        page = page or 1
        offset = (page - 1) * size
        limit = offset + size

        queryset = queryset[offset:limit]
        return queryset
