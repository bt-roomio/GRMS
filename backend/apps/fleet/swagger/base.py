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
