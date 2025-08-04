from djangochannelsrestframework.decorators import action


class SubscribeMixin:
    def __init__(self) -> None:
        self.subscribers = {}
        self.group_name = ""

    def add_group(self, name: str):
        raise NotImplementedError("You must implement add_group method.")

    @action()
    async def subscribe(self, request_id, action, query_params):
        await self.add_group(self.group_name)
        self.subscribers[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def unsubscribe(self, request_id):
        self.subscribers.pop(request_id, None)
