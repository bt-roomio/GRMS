"""
Celery side of the logging setup, connected from ``config/celery.py``:

- workers and beat keep Django's LOGGING instead of Celery's own root-logger
  setup, so every process shares one format and DJANGO_LOG_LEVEL;
- the publisher's request_id travels in the task headers, and each task runs
  with request_id/task_id/task in its log context.
"""

import logging.config

from celery import signals

from core.log.context import bind, get_context, new_request_id, unbind

REQUEST_ID_HEADER = "request_id"

# task_id -> context token; prerun and postrun of a task run in the same thread.
_tokens = {}


@signals.setup_logging.connect
def use_django_logging(**kwargs):
    # Having any receiver stops Celery from configuring the root logger itself
    # (and from applying the worker's -l/--loglevel to it).
    from django.conf import settings

    logging.config.dictConfig(settings.LOGGING)


@signals.before_task_publish.connect
def propagate_request_id(headers=None, **kwargs):
    request_id = get_context().get("request_id")
    if request_id and headers is not None:
        headers.setdefault(REQUEST_ID_HEADER, request_id)


@signals.task_prerun.connect
def bind_task_context(task_id=None, task=None, **kwargs):
    # Header from the publisher; for eager runs (.apply(), task_always_eager) the
    # caller's context is still active, so its request_id is reused.
    request_id = getattr(task.request, REQUEST_ID_HEADER, None) or get_context().get("request_id") or new_request_id()
    _tokens[task_id] = bind(request_id=request_id, task_id=task_id, task=task.name)


@signals.task_postrun.connect
def unbind_task_context(task_id=None, **kwargs):
    token = _tokens.pop(task_id, None)
    if token is not None:
        unbind(token)
