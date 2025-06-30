import logging
import threading
import time

import pika
from django.conf import settings
from django.core.management.base import BaseCommand
from pika.adapters.blocking_connection import BlockingChannel

from core.management.process_messages import process_messages

QUEUE_CONFIG = {
    "toGRMS": 1,
    "v1/devices/me/attributes/request": 1,
    "v1/gateway/rpc": 1,
    "v1/gateway/attributes/request": 1,
    "/attributes": 8,
    "/telemetry": 8,
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Command(BaseCommand):
    help = "Consumes messages from multiple RabbitMQ queues using dedicated threads with DLX support"

    def handle(self, *args, **options):
        try:
            credentials = pika.PlainCredentials(settings.RABBIT_LOGIN, settings.RABBIT_PASSWORD)
            parameters = pika.ConnectionParameters(settings.RABBIT_HOST, settings.RABBIT_PORT, "/", credentials)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            for queue_name in QUEUE_CONFIG.keys():
                channel.queue_declare(queue=queue_name, durable=True)

            connection.close()
        except Exception:
            logger.exception("Failed to setup queues!")
            return

        for queue_name, worker_count in QUEUE_CONFIG.items():
            for i in range(worker_count):
                thread = threading.Thread(target=self.worker_thread, args=(queue_name, i), daemon=True)
                thread.start()
                logger.debug(f"Started worker thread for queue '{queue_name}' (Worker-{i})")

        logger.info("All worker threads started. Waiting indefinitely...")
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")

    def worker_thread(self, queue_name: str, thread_id: int):
        while True:
            try:
                credentials = pika.PlainCredentials(settings.RABBIT_LOGIN, settings.RABBIT_PASSWORD)
                parameters = pika.ConnectionParameters(settings.RABBIT_HOST, settings.RABBIT_PORT, "/", credentials)
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()

                channel.queue_declare(queue=queue_name, durable=True, passive=True)
                channel.basic_qos(prefetch_count=1)

                def callback(
                    ch: BlockingChannel,
                    method: pika.spec.Basic.Deliver,
                    _: pika.BasicProperties,
                    body: bytes,
                ):
                    try:
                        process_messages(ch, method, body)
                        if method.delivery_tag:
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                            logger.debug(f"[{queue_name}][Worker-{thread_id}] Message processed successfully")
                    except Exception as e:
                        logger.warning(f"[{queue_name}][Worker-{thread_id}] Error processing message: {e}")

                channel.basic_consume(queue=queue_name, on_message_callback=callback)
                channel.start_consuming()

            except Exception as err:
                logger.exception(f"[{queue_name}][Worker-{thread_id}] Connection error: {err}")
                time.sleep(5)
