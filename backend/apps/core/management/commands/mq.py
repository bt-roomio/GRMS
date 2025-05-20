import logging
import threading

import pika
from django.conf import settings
from django.core.management.base import BaseCommand
from core.management.handlers_mq import handlers_mq

logger = logging.getLogger("main")
THREAD_COUNT = 8  # adjust to number of CPU cores or desired parallelism

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT
QUEUE_NAME = "toGRMS"


def _process_and_ack(ch, method, properties, body):
    try:
        handlers_mq(ch, body)
    except Exception as e:
        logger.exception("Error processing message: %s", e)
        # Nack with requeue=False to avoid infinite loop
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    else:
        ch.basic_ack(delivery_tag=method.delivery_tag)


def _worker_thread(connection_parameters):
    """Worker thread: opens its own connection and starts consuming."""
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    # Fair dispatch
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_process_and_ack)
    logger.info("Thread %s started consuming", threading.current_thread().name)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()

logger = logging.getLogger("main")

class Command(BaseCommand):
    help = "Multi-threaded RabbitMQ consumer"

    def handle(self, *args, **options):
        credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
        params = pika.ConnectionParameters(
            host=RABBIT_HOST if RABBIT_HOST != "localhost" else "127.0.0.1",
            port=RABBIT_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,  # pyright:ignore
            connection_attempts=5,
            retry_delay=2,  # pyright:ignore
        )

        threads = []
        for i in range(THREAD_COUNT):
            t = threading.Thread(
                target=_worker_thread,
                args=(params,),
                name=f"mq-worker-{i}",
                daemon=True,
            )
            threads.append(t)
            t.start()

        logger.info("Started %d worker threads", THREAD_COUNT)
        try:
            # Keep main thread alive
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            logger.info("Stopping all worker threads")
