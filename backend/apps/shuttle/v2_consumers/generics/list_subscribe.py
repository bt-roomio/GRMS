from djangochannelsrestframework.decorators import action


class ListSubscribeMixin:
    def __init__(self) -> None:
        self.subscribers = {}
        self.group_name = ""

    def add_group(self, name: str):
        raise NotImplementedError("You must implement add_group method.")

    def send_list(self, action, query_params, request_id, **kwargs):
        raise NotImplementedError("You must implement add_group method.")

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        await self.send_list(action, query_params, request_id, **kwargs)
        await self.add_group(self.group_name)
        self.subscribers[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)
