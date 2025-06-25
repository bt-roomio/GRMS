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
    "/attributes": 2,
    "/telemetry": 2,
}

DLX_EXCHANGE = "dlx_exchange"
DLX_QUEUE = "dlx_queue"
MESSAGE_TTL = 30000  # 30 seconds in milliseconds

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    help = "Consumes messages from multiple RabbitMQ queues using dedicated threads with DLX support"

    def setup_dlx(self, channel: BlockingChannel):
        """Setup Dead Letter Exchange and Queue"""
        try:
            channel.exchange_declare(exchange=DLX_EXCHANGE, exchange_type="fanout", durable=True)
            channel.queue_declare(queue=DLX_QUEUE, durable=True)
            channel.queue_bind(exchange=DLX_EXCHANGE, queue=DLX_QUEUE)

            logger.info(f"DLX setup completed: exchange={DLX_EXCHANGE}, queue={DLX_QUEUE}")
        except Exception as e:
            logger.error(f"Failed to setup DLX: {e}")
            raise

    def declare_queue_with_dlx(self, channel: BlockingChannel, queue_name: str):
        """Declare queue with DLX configuration"""
        try:
            args = {
                "x-dead-letter-exchange": DLX_EXCHANGE,
                "x-message-ttl": MESSAGE_TTL,  # Messages expire after TTL
            }

            channel.queue_declare(queue=queue_name, durable=True, arguments=args)  # pyright: ignore
        except Exception as e:
            logger.error(f"Failed to declare queue '{queue_name}' with DLX: {e}")
            raise

    def handle(self, *args, **options):
        try:
            credentials = pika.PlainCredentials(settings.RABBIT_LOGIN, settings.RABBIT_PASSWORD)
            parameters = pika.ConnectionParameters(settings.RABBIT_HOST, settings.RABBIT_PORT, "/", credentials)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            self.setup_dlx(channel)

            for queue_name in QUEUE_CONFIG.keys():
                self.declare_queue_with_dlx(channel, queue_name)

            connection.close()
        except Exception as e:
            logger.error(f"Failed to setup DLX and queues: {e}")
            return

        for queue_name, worker_count in QUEUE_CONFIG.items():
            for i in range(worker_count):
                thread = threading.Thread(target=self.worker_thread, args=(queue_name, i), daemon=True)
                thread.start()
                logger.info(f"Started worker thread for queue '{queue_name}' (Worker-{i})")

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
                        if method.delivery_tag:
                            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                            logger.info(f"[{queue_name}][Worker-{thread_id}] Message rejected and sent to DLX")

                channel.basic_consume(queue=queue_name, on_message_callback=callback)
                channel.start_consuming()

            except Exception as err:
                logger.exception(f"[{queue_name}][Worker-{thread_id}] Connection error: {err}")
                time.sleep(5)
