import os

from config.settings.components import env_list

# Purge of selected shuttle_ts_kv keys (device logs, events, errors); the rest of the
# telemetry is kept. Glob patterns matched case-sensitively against TsKvDictionary.key,
# space-separated, e.g. TSKV_PURGE_KEYS="*_LOGS". Empty disables it.
TSKV_PURGE_KEYS = env_list("TSKV_PURGE_KEYS")
# Rows of those keys are deleted once their whole day (chunk) is older than this.
TSKV_PURGE_AFTER_DAYS = int(os.getenv("TSKV_PURGE_AFTER_DAYS", "30"))
