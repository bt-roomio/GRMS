import os

from config.settings.components import env_bool

# Alarms — ThingsBoard-style alarm rules on device profiles

# Kill switch: turns off the evaluator and the dispatcher without rolling back
# the image, for when a hand-written rule misbehaves in production.
ALARMS_ENABLED = env_bool("ALARMS_ENABLED", "true")
# How often the evaluator sweeps TsKvLatest/AttributeKv. This is also the
# worst-case delay between a condition becoming true and its alarm appearing.
ALARMS_EVAL_INTERVAL_SEC = int(os.getenv("ALARMS_EVAL_INTERVAL_SEC", "30"))
# Cleared alarms older than this are purged nightly; open ones never are.
ALARMS_TTL_DAYS = int(os.getenv("ALARMS_TTL_DAYS", "365"))

# One bot for the whole installation, a chat id per tenant — the token never
# leaves the server, and tenants only ever configure where messages land.
# Unrelated to the TELEGRAM_* pair in deploy/monitoring: that is Alertmanager's
# own compose stack and its own env file.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org").rstrip("/")
TELEGRAM_TIMEOUT = float(os.getenv("TELEGRAM_TIMEOUT", "10"))

# WhatsApp Cloud API. Unlike Telegram there is no installation-wide sender:
# every hotel sends from its own number, with credentials kept in its
# notification settings, so Meta bills the hotel. WA_VERIFY_TOKEN is an
# arbitrary string typed into the Meta webhook form (not an access token);
# WA_APP_SECRET signs every webhook POST, and an empty one refuses them all.
WA_APP_SECRET = os.getenv("WA_APP_SECRET", "")
WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "")
WA_GRAPH_VERSION = os.getenv("WA_GRAPH_VERSION", "v21.0")
WA_TIMEOUT = float(os.getenv("WA_TIMEOUT", "10"))
# The approved Utility template alarms go out with (see alarms.channels.whatsapp).
WA_ALARM_TEMPLATE = os.getenv("WA_ALARM_TEMPLATE", "alarm_summary")
WA_TEMPLATE_LANGUAGE = os.getenv("WA_TEMPLATE_LANGUAGE", "ru")
