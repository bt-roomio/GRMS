"""Static configuration for the async MQ consumer.

Queue names, message topics, batching parameters and the RabbitMQ connection
settings live here so the rest of the ``mq`` package imports them from a single
place instead of redefining constants.
"""

from django.conf import settings

# Queue Names
QUEUE_TO_GRMS = "toGRMS"
QUEUE_FROM_GRMS = "fromGRMS"
QUEUE_DEVICE_ATTRS_REQUEST = "v1/devices/me/attributes/request"
QUEUE_GATEWAY_RPC = "v1/gateway/rpc"
QUEUE_GATEWAY_ATTRS_REQUEST = "v1/gateway/attributes/request"
QUEUE_ATTRIBUTES = "/attributes"
QUEUE_TELEMETRY = "/telemetry"

QUEUE_CONFIG = [
    QUEUE_TO_GRMS,
    QUEUE_DEVICE_ATTRS_REQUEST,
    QUEUE_GATEWAY_RPC,
    QUEUE_GATEWAY_ATTRS_REQUEST,
    QUEUE_ATTRIBUTES,
    QUEUE_TELEMETRY,
]

# Message Topics
TOPIC_TELEMETRY = "/telemetry"
TOPIC_ATTRIBUTES = "/attributes"
TOPIC_GATEWAY_CONNECT = "v1/gateway/connect"
TOPIC_GATEWAY_DISCONNECT = "v1/gateway/disconnect"
TOPIC_GATEWAY_ATTRIBUTES_REQUEST = "v1/gateway/attributes/request"
TOPIC_DEVICES_ATTRIBUTES_REQUEST = "v1/devices/me/attributes/request"
TOPIC_GATEWAY_RPC = "v1/gateway/rpc"

# Batch processing configuration
BATCH_SIZE = 200
BATCH_TIMEOUT = 0.3  # 300ms
PREFETCH_COUNT = 1000

# Device cache expiry in Redis (seconds)
DEVICE_CACHE_EXPIRY = 600  # 10 minutes

# RabbitMQ connection
RB_LOGIN = settings.RABBIT_LOGIN
RB_PASSWORD = settings.RABBIT_PASSWORD
RB_HOST = settings.RABBIT_HOST
RB_PORT = settings.RABBIT_PORT

AMQP_URL = f"amqp://{RB_LOGIN}:{RB_PASSWORD}@{RB_HOST}:{RB_PORT}/"
RECONNECT_INTERVAL = 5
