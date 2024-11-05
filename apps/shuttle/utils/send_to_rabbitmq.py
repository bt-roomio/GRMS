import json

import pika
from django.conf import settings

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT


def connect_to_rabbitmq():
    credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
    parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    return channel


def send_to_rabbitmq(message: dict):
    channel = connect_to_rabbitmq()
    message = json.dumps(message, indent=2).encode("utf-8")
    channel.basic_publish(exchange="", routing_key="fromGRMS", body=message)
    return channel


def send_to_rabbitmq_device_me(device_id, attributes, topic, request_id=None):
    channel = connect_to_rabbitmq()
    message_data = {"targetDeviceUUID": str(device_id), "topic": topic, "data": attributes}
    if request_id:
        message_data["data"]["id"] = request_id
    message = json.dumps(message_data, indent=2).encode("utf-8")
    topic_name = "fromGRMS"

    channel.basic_publish(exchange="", routing_key=topic_name, body=message)
