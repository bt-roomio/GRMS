import logging

from core.tasks import process_mq_message


def handlers_mq(body: bytes):
    logger = logging.getLogger(__name__)
    logger.info(f"Scheduling task, body: {body}")
    process_mq_message.delay(body.decode("utf-8"))  # pyright:ignore
