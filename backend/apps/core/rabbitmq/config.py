import json

import pika
from django.conf import settings
from pika.adapters.blocking_connection import BlockingChannel

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT


def send_to_rabbitmq(channel: BlockingChannel, message, routing_key="fromGRMS"):
    message = json.dumps(message).encode("utf-8")
    channel.basic_publish(exchange="", routing_key=routing_key, body=message)
    return channel


def connect_to_rabbitmq() -> BlockingChannel:
    credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
    parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    return channel
