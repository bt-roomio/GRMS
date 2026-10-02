import os
import re

from config.settings.components import env_bool

PROMETHEUS_MULTIPROC_DIR = os.environ.get("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc")
os.makedirs(PROMETHEUS_MULTIPROC_DIR, exist_ok=True)
os.environ["PROMETHEUS_MULTIPROC_DIR"] = PROMETHEUS_MULTIPROC_DIR

# Gateway monitoring settings
DJANGO_IS_MONITORING_GATEWAYS = env_bool("DJANGO_IS_MONITORING_GATEWAYS", "True")
DJANGO_MONITORING_EXCLUDED_GATEWAYS = list(
    filter(None, re.split(r"[,\s]+", os.getenv("DJANGO_MONITORING_EXCLUDED_GATEWAYS", "")))
)
