from asgiref.sync import iscoroutinefunction, markcoroutinefunction

from core.log.context import bind, clean_request_id, current_request, unbind

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware:
    """
    Binds a request id (the inbound X-Request-ID, or a fresh one) and the request
    itself to the log context, and returns the id in the X-Request-ID response
    header so a client/nginx log line can be matched with the backend's.

    Supports both sync and async stacks, so it adds no thread hop under ASGI.
    Keep it near the top of MIDDLEWARE so the other middleware log with the id.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def _enter(self, request):
        request.request_id = clean_request_id(request.headers.get(REQUEST_ID_HEADER))
        return bind(request_id=request.request_id), current_request.set(request)

    def _exit(self, tokens):
        context_token, request_token = tokens
        current_request.reset(request_token)
        unbind(context_token)

    def __call__(self, request):
        if iscoroutinefunction(self):
            return self.__acall__(request)
        tokens = self._enter(request)
        try:
            response = self.get_response(request)
        finally:
            self._exit(tokens)
        response[REQUEST_ID_HEADER] = request.request_id
        return response

    async def __acall__(self, request):
        tokens = self._enter(request)
        try:
            response = await self.get_response(request)
        finally:
            self._exit(tokens)
        response[REQUEST_ID_HEADER] = request.request_id
        return response
