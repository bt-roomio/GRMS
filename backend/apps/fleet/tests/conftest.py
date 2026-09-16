"""
The SSH-server fixtures live in `fleet.tests.sshd` so that the terminal consumer
tests — which sit under shuttle with the other consumer tests — can reuse them.
pytest only discovers fixtures through a conftest, hence this re-export.
"""

from fleet.tests.sshd import client_key, sshd, upload_root  # noqa: F401
