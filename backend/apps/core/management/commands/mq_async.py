"""Standalone entry point for the async RabbitMQ consumer.

Run directly (not as a Django management subcommand):

    python apps/core/management/commands/mq_async.py

The actual consumer logic lives in the :mod:`core.management.mq` package; this
module only bootstraps Django and hands off to :func:`core.management.mq.engine.runner.run`.
"""

import os
import sys
from pathlib import Path

import django

# Add backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Initialize Django before importing anything that touches settings or models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
# ruff: noqa: E402
from core.management.mq.engine.runner import run

if __name__ == "__main__":
    run()
