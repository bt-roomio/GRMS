import os

# Fleet — remote management of hotel VMs over the NetBird mesh

NETBIRD_API_URL = os.getenv("NETBIRD_API_URL", "").rstrip("/")
NETBIRD_PAT = os.getenv("NETBIRD_PAT", "")
NETBIRD_HOTEL_GROUP_ID = os.getenv("NETBIRD_HOTEL_GROUP_ID", "")
NETBIRD_MANAGEMENT_URL = os.getenv("NETBIRD_MANAGEMENT_URL", "") or os.getenv("WEBRTC_BROKER_URL", "")
NETBIRD_TIMEOUT = float(os.getenv("NETBIRD_TIMEOUT", "10"))
NETBIRD_SETUP_KEY_TTL = int(os.getenv("NETBIRD_SETUP_KEY_TTL", "3600"))

# "derive it from FRONTEND_DOMAIN" — see `fleet.utils.code.node_prefix`.
FLEET_NODE_PREFIX = os.getenv("FLEET_NODE_PREFIX", "")

# The private half of the fleet keypair. Stays on this server, never leaves.
FLEET_SSH_PRIVATE_KEY_PATH = os.path.expanduser(os.getenv("SSH_PRIVATE_KEY_PATH", "~/.roomio/fleet_key"))
# The public half, injected into the bootstrap script and installed on every node.
FLEET_SSH_PUBLIC_KEY = os.getenv("SSH_PUBLIC_KEY", "")
FLEET_SSH_USER = os.getenv("SSH_USER", "roomio-agent")
FLEET_SSH_PORT = int(os.getenv("SSH_PORT", "22"))
FLEET_SSH_CONNECT_TIMEOUT = float(os.getenv("FLEET_SSH_CONNECT_TIMEOUT", "15"))
FLEET_SSH_COMMAND_TIMEOUT = float(os.getenv("FLEET_SSH_COMMAND_TIMEOUT", "60"))

FLEET_UPLOAD_ROOT = os.getenv("FLEET_UPLOAD_ROOT", "")
FLEET_UPLOAD_MAX_BYTES = int(os.getenv("FLEET_UPLOAD_MAX_BYTES", str(100 * 1024 * 1024)))
FLEET_UPLOAD_TIMEOUT = float(os.getenv("FLEET_UPLOAD_TIMEOUT", "300"))

FLEET_GATEWAY_SERVICE = os.getenv("FLEET_GATEWAY_SERVICE", "roomio-gateway")
FLEET_JOB_CONCURRENCY = int(os.getenv("FLEET_JOB_CONCURRENCY", "5"))
FLEET_JOB_MAX_NODES = int(os.getenv("FLEET_JOB_MAX_NODES", "200"))
FLEET_JOB_OUTPUT_LIMIT = int(os.getenv("FLEET_JOB_OUTPUT_LIMIT", str(64 * 1024)))
FLEET_JOB_TIMEOUT = float(os.getenv("FLEET_JOB_TIMEOUT", "1800"))

FLEET_INSTALL_TOKEN_TTL_HOURS = int(os.getenv("INSTALL_TOKEN_TTL_HOURS", "24"))
# Public base URL used to build the `curl ... | sudo bash` one-liner.
FLEET_INSTALL_BASE_URL = os.getenv("FLEET_INSTALL_BASE_URL", "").rstrip("/")
