import logging
import sys
from types import SimpleNamespace

import orjson
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.utils.functional import SimpleLazyObject

from core.log import celery as log_celery
from core.log.context import current_request, get_context, log_context
from core.log.filters import ContextFilter
from core.log.formatters import JSONFormatter
from core.log.middleware import REQUEST_ID_HEADER, RequestContextMiddleware


def _record(msg="hello %s", args=("world",), exc_info=None):
    return logging.LogRecord("app.module", logging.INFO, __file__, 10, msg, args, exc_info)


class ContextFilterTests(SimpleTestCase):
    def test_no_context_renders_empty_prefix(self):
        record = _record()
        ContextFilter().filter(record)
        self.assertEqual(record.log_context, {})
        self.assertEqual(record.ctx, "")

    def test_bound_context_is_stamped(self):
        record = _record()
        with log_context(request_id="abc", task="t"):
            ContextFilter().filter(record)
        self.assertEqual(record.log_context, {"request_id": "abc", "task": "t"})
        self.assertEqual(record.ctx, "[request_id=abc task=t] ")

    def test_nested_context_is_restored(self):
        with log_context(a=1):
            with log_context(b=2):
                self.assertEqual(get_context(), {"a": 1, "b": 2})
            self.assertEqual(get_context(), {"a": 1})
        self.assertEqual(get_context(), {})

    def test_authenticated_request_user_and_tenant(self):
        user = SimpleNamespace(pk=7, is_authenticated=True, tenant_id="t-1")
        request = SimpleNamespace(user=user)
        token = current_request.set(request)
        try:
            record = _record()
            ContextFilter().filter(record)
        finally:
            current_request.reset(token)
        self.assertEqual(record.log_context, {"user_id": 7, "tenant_id": "t-1"})

    def test_unevaluated_lazy_user_is_not_resolved(self):
        def fail():
            raise AssertionError("logging must not evaluate request.user")

        request = SimpleNamespace(user=SimpleLazyObject(fail))
        token = current_request.set(request)
        try:
            record = _record()
            ContextFilter().filter(record)
        finally:
            current_request.reset(token)
        self.assertEqual(record.log_context, {})


class JSONFormatterTests(SimpleTestCase):
    def test_payload(self):
        record = _record()
        record.device = "d1"  # as if passed via extra=
        with log_context(request_id="abc"):
            ContextFilter().filter(record)
        payload = orjson.loads(JSONFormatter().format(record))
        self.assertEqual(payload["message"], "hello world")
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "app.module")
        self.assertEqual(payload["request_id"], "abc")
        self.assertEqual(payload["device"], "d1")
        self.assertNotIn("ctx", payload)
        self.assertNotIn("exc_info", payload)

    def test_exception(self):
        try:
            raise ValueError("boom")
        except ValueError:
            record = _record(exc_info=sys.exc_info())
        payload = orjson.loads(JSONFormatter().format(record))
        self.assertIn("ValueError: boom", payload["exc_info"])


class RequestContextMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.seen = {}

        def view(request):
            self.seen.update(get_context())
            return HttpResponse()

        self.middleware = RequestContextMiddleware(view)

    def test_generates_request_id(self):
        response = self.middleware(RequestFactory().get("/"))
        request_id = response[REQUEST_ID_HEADER]
        self.assertEqual(len(request_id), 32)
        self.assertEqual(self.seen["request_id"], request_id)
        self.assertEqual(get_context(), {})
        self.assertIsNone(current_request.get())

    def test_keeps_valid_inbound_id(self):
        response = self.middleware(RequestFactory().get("/", HTTP_X_REQUEST_ID="edge-123"))
        self.assertEqual(response[REQUEST_ID_HEADER], "edge-123")

    def test_replaces_unsafe_inbound_id(self):
        response = self.middleware(RequestFactory().get("/", HTTP_X_REQUEST_ID="bad id\nwith newline"))
        self.assertNotEqual(response[REQUEST_ID_HEADER], "bad id\nwith newline")
        self.assertEqual(len(response[REQUEST_ID_HEADER]), 32)


class CeleryContextTests(SimpleTestCase):
    def test_publish_carries_request_id(self):
        headers = {}
        with log_context(request_id="abc"):
            log_celery.propagate_request_id(headers=headers)
        self.assertEqual(headers, {"request_id": "abc"})

    def test_publish_without_context_adds_nothing(self):
        headers = {}
        log_celery.propagate_request_id(headers=headers)
        self.assertEqual(headers, {})

    def test_task_context_bound_and_released(self):
        task = SimpleNamespace(name="app.tasks.job", request=SimpleNamespace(request_id="abc"))
        log_celery.bind_task_context(task_id="t1", task=task)
        self.assertEqual(get_context(), {"request_id": "abc", "task_id": "t1", "task": "app.tasks.job"})
        log_celery.unbind_task_context(task_id="t1")
        self.assertEqual(get_context(), {})

    def test_eager_task_inherits_caller_request_id(self):
        task = SimpleNamespace(name="app.tasks.job", request=SimpleNamespace())
        with log_context(request_id="caller"):
            log_celery.bind_task_context(task_id="t3", task=task)
            try:
                self.assertEqual(get_context()["request_id"], "caller")
            finally:
                log_celery.unbind_task_context(task_id="t3")

    def test_task_without_inbound_id_gets_fresh_one(self):
        task = SimpleNamespace(name="app.tasks.job", request=SimpleNamespace())
        log_celery.bind_task_context(task_id="t2", task=task)
        try:
            self.assertEqual(len(get_context()["request_id"]), 32)
        finally:
            log_celery.unbind_task_context(task_id="t2")
