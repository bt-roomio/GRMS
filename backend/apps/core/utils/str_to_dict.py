import json
import logging

logger = logging.getLogger("django")


def str_to_dict(msg):
    if type(msg) is dict:
        return msg
    try:
        if msg.startswith('"') and msg.endswith('"'):
            msg = msg[1:-1]

        msg = msg.replace('\\"', '"')

        return json.loads(msg)
    except Exception as e:
        logger.warning(f"Second attempt failed: {e}")
        return msg
