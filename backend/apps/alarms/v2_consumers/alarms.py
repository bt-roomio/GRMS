from djangochannelsrestframework.observer.generics import action

from alarms.models import Alarm
from alarms.serializers.alarm import AlarmFilterParams, AlarmSerializer
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class AlarmConsumer(BaseGenericAsyncAPIConsumer):
    """
    Live alarm list.

    The successor to the ``current_alarms`` stream, which only ever knew about
    ``AttributeKv.active == false``. That one stays until the front end has
    moved over; see docs/alarms.md.
    """

    queryset = Alarm.objects.all()
    serializer_class = AlarmSerializer

    def get_queryset(self, **kwargs):
        params = AlarmFilterParams.check(kwargs.get("query_params") or {})
        return Alarm.objects.list(
            tenant_id=self.tenant_id,
            types=params.get("alarm_type"),
            severities=params.get("severity"),
            # Default to the live list; the journal is what the REST endpoint is for.
            status=params.get("status", "ACTIVE"),
            device_id=params.get("device"),
            room_id=params.get("room"),
            assignee_id=params.get("assignee"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )

    @action()
    async def list(self, **kwargs):
        return await self.send_list_paginated(**kwargs), 200

    @action()
    async def list_subscribe(self, **kwargs):
        await self.send_list_paginated(**kwargs)
        await self.add_group(f"alarms_{self.tenant_id}")
        self.subscribers[kwargs.get("request_id")] = kwargs

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.remove_group(f"alarms_{self.tenant_id}")
        self.subscribers.pop(request_id, None)

    async def alarm_update(self, message):
        for request_id, params in self.subscribers.items():
            await self.send_list_paginated(
                action=params.get("action"),
                query_params=params.get("query_params", {}),
                request_id=request_id,
            )
