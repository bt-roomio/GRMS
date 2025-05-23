import logging
import threading
import time

import pika
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
    "/attributes": 2,
    "/telemetry": 2,
}

logger = logging.getLogger("main")


class Command(BaseCommand):
    help = "Consumes messages from multiple RabbitMQ queues using dedicated threads"

    def handle(self, *args, **options):
        for queue_name, worker_count in QUEUE_CONFIG.items():
            for i in range(worker_count):
                thread = threading.Thread(target=self.worker_thread, args=(queue_name, i), daemon=True)
                thread.start()

        # Ожидаем завершения всех потоков (по сути — бесконечно)
        while True:
            time.sleep(10)

    def worker_thread(self, queue_name: str, thread_id: int):
        while True:
            try:
                credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
                parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                channel.queue_declare(queue=queue_name, durable=True)
                channel.basic_qos(prefetch_count=1)

                logger.info(f"[{queue_name}][Worker-{thread_id}] Started consuming")

                def callback(ch, method, properties, body):
                    try:
                        handlers_mq(ch, body)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.warning(f"[{queue_name}][Worker-{thread_id}] Error: {e}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                channel.basic_consume(queue=queue_name, on_message_callback=callback)
                channel.start_consuming()

            except Exception as err:
                logger.exception(f"[{queue_name}][Worker-{thread_id}] Connection error: {err}")
                time.sleep(5)
