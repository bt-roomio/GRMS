"""
Logging infrastructure: per-request/per-task context, the filter that stamps it
onto every record, the JSON formatter and the glue for HTTP and Celery.

Wired up in ``config/settings/components/logging.py``. Modules here must not
import models: the logging config is applied while Django is still setting up.
"""
