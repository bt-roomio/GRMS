TAG = "Fleet"

NODE_DESCRIPTION = """
**A `FleetNode` is the VM that hosts one gateway.**

Exactly one active node per gateway, so the gateway is the node's identity: it
decides the tenant, and it decides `code`, which is generated as
`{tenant_name}_{gateway_name}` and used verbatim as the NetBird peer name.

A node is reachable only over the NetBird mesh, and `is_online` reflects mesh
connectivity — not application health.

Nearly every field is assigned by the system, never sent by the client:
`mesh_ip` / `is_online` / `last_seen` / `os` / `netbird_version` come from the
NetBird poller, and `ssh_user` comes from settings.
"""

JOB_DESCRIPTION = """
**A `FleetJob` is one catalog action fanned out over many nodes.**

The client picks an `action` from `GET /fleet/actions/` and a set of targets; the
command itself is built on the server, so a job can never carry free-form shell.
(`POST /nodes/{id}/run/` remains the single-node escape hatch.)

Every targeted node gets a `FleetJobTask` row when the job is created, before
anything runs — the total is known immediately, and a node that is skipped shows
up as skipped rather than missing.

Execution is asynchronous, a few nodes at a time. Poll `GET /fleet/jobs/{id}/`,
or stop the rest with `POST /fleet/jobs/{id}/cancel/`.
"""
