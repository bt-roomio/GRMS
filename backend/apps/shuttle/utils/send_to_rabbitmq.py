import json

import pika
from django.conf import settings

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT


def send_to_rabbitmq(device_id, device_name, attributes):
    channel = connect_to_rabbitmq()
    message_data = {
        "targetDeviceUUID": str(device_id),
        "topic": "v1/gateway/attributes",
        "data": {"device": device_name, "data": attributes},
    }
    message = json.dumps(message_data, indent=2).encode("utf-8")
    topic_name = "fromGRMS"

    channel.basic_publish(exchange="", routing_key=topic_name, body=message)


def connect_to_rabbitmq():
    credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
    parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    return channel
