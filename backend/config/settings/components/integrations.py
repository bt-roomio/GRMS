import os

from config.settings.components import env_list

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = os.getenv("RABBIT_PORT", "5672")
RABBIT_LOGIN = os.getenv("RABBIT_LOGIN", "guest")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", "guest")

WEBRTC_BROKER_URL = os.getenv("WEBRTC_BROKER_URL")

WS_INTERVAL = os.getenv("WS_INTERVAL", "5")

HOTEZA_WHITELIST = env_list("HOTEZA_WHITELIST")

CLIENT_TOKENS = os.getenv("CLIENT_TOKENS", "").split(" ")
