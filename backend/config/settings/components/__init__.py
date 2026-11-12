"""
Shared bootstrap for the settings components.

Imported once, before any component is included: loads .env, puts apps/ on
sys.path and provides the env-parsing helpers the components share.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Append module dir
if str(BASE_DIR / "apps") not in sys.path:
    sys.path.append(os.path.join(BASE_DIR, "apps"))


def env_bool(name: str, default: str = "") -> bool:
    """Read a boolean flag: "1", "true" or "yes" (any case) mean True."""
    return os.getenv(name, default).lower() in ("1", "true", "yes")


def env_list(name: str) -> list[str]:
    """Read a space-separated list, e.g. 'DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]'."""
    return list(filter(None, os.getenv(name, "").split(" ")))
