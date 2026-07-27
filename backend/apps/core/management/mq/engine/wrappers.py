"""Bridge sync batch handlers into the asyncio event loop.

The heavy handlers (telemetry, attributes, RPC) are synchronous and run in the
default thread pool via ``sync_to_async(..., thread_sensitive=False)``. Thread
pool threads are reused between batches, so each call is wrapped with
``_db_safe`` to drop stale PgBouncer connections before/after execution.
"""

from asgiref.sync import sync_to_async

from core.management.mq.db_safe import _db_safe
from core.management.mq.handlers.attributes import sync_attributes_batch
from core.management.mq.handlers.rpc_message import handle_rpc
from core.management.mq.handlers.telemetry import sync_telemetry_batch

# Wrap sync batch functions (thread_sensitive=False allows parallel execution in thread pool)
sync_telemetry_batch_async = sync_to_async(_db_safe(sync_telemetry_batch), thread_sensitive=False)
sync_attributes_batch_async = sync_to_async(_db_safe(sync_attributes_batch), thread_sensitive=False)
# sync_state_device_batch_async is already async, imported directly where needed.

# Wrap individual handlers
handle_rpc_async = sync_to_async(_db_safe(handle_rpc), thread_sensitive=False)
