import logging

import pika
from django.conf import settings
from django.core.management.base import BaseCommand
from pika.adapters.blocking_connection import BlockingChannel

from core.management.handlers_mq import handlers_mq

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT

logger = logging.getLogger("main")


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def handle(self, *args, **options):
        try:
            credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
            connection_parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)

            with pika.BlockingConnection(connection_parameters) as conn:
                with conn.channel() as ch:
                    ch.queue_declare(queue="toGRMS")
                    ch.basic_consume(queue="toGRMS", on_message_callback=self.process_message)
                    print("Waiting for message")
                    ch.start_consuming()
        except Exception as err:
            logger.warn(str(err))

    def process_message(
        self,
        ch: BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ):
        try:
            handlers_mq(ch, body)
        except Exception as err:
            logger.warning("Error from handlers_mq", err)
            return

        # Make sure this should end of process
        if method and method.delivery_tag:
            ch.basic_ack(delivery_tag=method.delivery_tag)
