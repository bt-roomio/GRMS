import asyncio
import logging

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage
from django.conf import settings
from django.core.management.base import BaseCommand

from core.management.handlers_mq import handlers_mq

logger = logging.getLogger("main")

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT

EXCHANGE_NAME = "toGRMS"

TOPIC_BINDINGS = {
    "rpc": "v1.gateway.rpc",
    "connect": "v1.gateway.connect",
    "disconnect": "v1.gateway.disconnect",
    "attributes": "#.attributes",
    "telemetry": "#.telemetry",
}


class Command(BaseCommand):
    help = "Handle messages from rabbit_mq"

    def handle(self, *args, **options):
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("MQ consumer stopped")


async def handle_message(message: AbstractIncomingMessage):
    async with message.process(ignore_processed=True):
        try:
            await asyncio.to_thread(handlers_mq, body=message.body)
        except Exception as e:
            logger.exception("Error processing message: %s", e)


async def start_consumer(channel: AbstractChannel, topic_key: str, binding_key: str):
    queue = await channel.declare_queue(EXCHANGE_NAME, durable=True)
    await queue.bind(exchange=await channel.get_exchange(EXCHANGE_NAME), routing_key=binding_key)
    await queue.consume(handle_message)
    logger.info("Consumer started: queue=%s bind=%s", EXCHANGE_NAME, binding_key)


async def main():
    # подключаемся к RabbitMQ (robust для автоматического переподключения)
    connection = await aio_pika.connect_robust(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        login=RABBIT_LOGIN,
        password=RABBIT_PASSWORD,
    )

    async with connection:
        # канал для всех очередей
        channel = await connection.channel()
        # прямой обмен типа topic
        await channel.declare_exchange(EXCHANGE_NAME, ExchangeType.TOPIC, durable=True)

        # запускаем консьюмеры по каждой теме
        tasks = []
        for topic_key, binding_key in TOPIC_BINDINGS.items():
            tasks.append(asyncio.create_task(start_consumer(channel, topic_key, binding_key)))

        # держим приложение живым
        await asyncio.gather(*tasks)
        await asyncio.Future()  # блокируем навечно
