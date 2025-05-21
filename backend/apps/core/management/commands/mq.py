import logging
import pika
import threading
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.core.management.base import BaseCommand

from core.management.handlers_mq import handlers_mq

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT

# Очереди и количество потоков для каждой
QUEUE_CONFIG = {
    "toGRMS": 1,
    "v1/devices/me/attributes/request": 1,
    "v1/gateway/rpc": 1,
    "v1/gateway/attributes/request": 1,
    "/attributes": 1,
    "/telemetry": 1,
}

logger = logging.getLogger("main")


class Command(BaseCommand):
    help = "Consumes messages from multiple RabbitMQ queues using thread pools"

    def handle(self, *args, **options):
        threads = []
        for queue_name, worker_count in QUEUE_CONFIG.items():
            t = threading.Thread(target=self.consume_queue, args=(queue_name, worker_count), daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    def consume_queue(self, queue_name: str, worker_count: int):
        while True:
            try:
                credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
                connection_parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)

                connection = pika.BlockingConnection(connection_parameters)
                channel = connection.channel()
                channel.queue_declare(queue=queue_name)
                channel.basic_qos(prefetch_count=worker_count)

                executor = ThreadPoolExecutor(max_workers=worker_count)

                def callback(ch, method, properties, body):
                    executor.submit(self.process_message, queue_name, ch, method, properties, body)

                channel.basic_consume(queue=queue_name, on_message_callback=callback)
                logger.info(f"Started consuming from '{queue_name}' with {worker_count} threads")
                channel.start_consuming()

            except Exception as err:
                logger.exception(f"[{queue_name}] Error in consumer thread: {err}")

    def process_message(self, queue_name, ch, method, properties, body):
        try:
            handlers_mq(ch, body)
            if ch.is_open:
                ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as err:
            logger.warning(f"[{queue_name}] Error processing message: {body}. Error: {err}")