import os

from config.settings.components import env_list

# Purge of selected shuttle_ts_kv keys (device logs, events, errors); the rest of the
# telemetry is kept. Glob patterns matched case-sensitively against TsKvDictionary.key,
# space-separated, e.g. TSKV_PURGE_KEYS="*_LOGS". Empty disables it.
TSKV_PURGE_KEYS = env_list("TSKV_PURGE_KEYS")
# Rows of those keys are deleted once their whole day (chunk) is older than this.
TSKV_PURGE_AFTER_DAYS = int(os.getenv("TSKV_PURGE_AFTER_DAYS", "30"))

# Redis cache of the ts_kv_history WebSocket stream (aggregated chart data, see
# shuttle/services/ts_kv_history_cache.py). An entry lives for one 60th of its bucket width, clamped
# to [MIN, MAX] seconds (1 hour -> 60 s, 1 day -> MAX), and is dropped as soon as the device gets new
# ts_kv rows. TSKV_HISTORY_CACHE_MAX_TTL=0 disables the cache.
TSKV_HISTORY_CACHE_MIN_TTL = int(os.getenv("TSKV_HISTORY_CACHE_MIN_TTL", "30"))
TSKV_HISTORY_CACHE_MAX_TTL = int(os.getenv("TSKV_HISTORY_CACHE_MAX_TTL", "300"))
