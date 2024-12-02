import logging

import pika
from django.conf import settings
from django.core.management.base import BaseCommand

from shuttle.tasks import process_mq

logger = logging.getLogger(__name__)
logger.critical("Now logging consumer command")

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT

rabbit_queues = {"toGRMSqueueName": "toGRMS", "fromGRMSqueueName": "fromGRMS"}


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def handle(self, *args, **options):
        consume()


def consume():
    channel = connect_to_rabbitmq()

    def message_handler(ch, method, properties, body):
        process_mq.delay(body)

    channel.basic_consume(queue=rabbit_queues["toGRMSqueueName"], on_message_callback=message_handler, auto_ack=True)
    logger.critical("Waiting for messages in topic. To exit press CTRL+C")
    channel.start_consuming()


def connect_to_rabbitmq():
    credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
    parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    return channel
