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


def main():
    # Imported inside the function (not at module top) so it runs after
    # django.setup(). A function-body import is not a module-level import, so
    # E402 never applies — no noqa that tooling would disagree about.
    from core.management.mq.engine.runner import run

    run()


if __name__ == "__main__":
    main()
