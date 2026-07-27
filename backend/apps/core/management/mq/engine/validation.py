"""Message-inspection helpers for the MQ consumer.

``_extract_keys`` pulls the telemetry/attribute key names used for metric labels.
Device resolution happens in batch in :mod:`core.management.mq.devices.device_resolver`.
"""


def _extract_keys(topic: str, data) -> list[str]:
    keys: list[str] = []
    if topic.endswith("/telemetry"):
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    keys.extend(entry.get("values", {}).keys())
        elif isinstance(data, dict):
            for device_data in data.values():
                if isinstance(device_data, list):
                    for entry in device_data:
                        if isinstance(entry, dict):
                            keys.extend(entry.get("values", {}).keys())
    elif topic.endswith("/attributes"):
        if isinstance(data, dict):
            first_val = next(iter(data.values()), None)
            if isinstance(first_val, dict):
                for sub in data.values():
                    if isinstance(sub, dict):
                        keys.extend(sub.keys())
            else:
                keys.extend(data.keys())
    return list(set(keys))
