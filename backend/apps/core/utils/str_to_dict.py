import json
import logging

logger = logging.getLogger("django")


def str_to_dict(input):
    if type(input) is dict:
        return input
    try:
        if input.startswith('"') and input.endswith('"'):
            input = input[1:-1]

        input = input.replace('\\"', '"')

        return json.loads(input)
    except Exception as e:
        logger.warning(f"Second attempt failed: {e}")
        return input
