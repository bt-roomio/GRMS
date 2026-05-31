import time

from core.management.mq.fias.constants import KEYREQUEST_COLLECTION_TIMEOUT
from core.management.mq.fias.exceptions import LookupFailure
from shuttle.models import AttributeKv


def _read_card_uid(reader_device_id):
    card_uid_attr = AttributeKv.objects.filter(
        entity_id=reader_device_id,
        attribute_type=AttributeKv.CLIENT_SCOPE,
        attribute_key="card_uid",
    ).first()
    return card_uid_attr.str_v if card_uid_attr else None


def collect_unique_cards(reader_device_id, count, timeout=KEYREQUEST_COLLECTION_TIMEOUT):
    collected = []
    seen = set()
    deadline = time.time() + timeout

    while len(collected) < count:
        if time.time() >= deadline:
            raise LookupFailure(f"Timeout: collected {len(collected)} of {count} cards")

        on_reader = AttributeKv.objects.filter(
            entity_id=reader_device_id,
            attribute_type=AttributeKv.CLIENT_SCOPE,
            attribute_key="card_on_reader",
            bool_v=True,
        ).exists()
        if on_reader:
            uid = _read_card_uid(reader_device_id)
            if uid and uid not in seen:
                seen.add(uid)
                collected.append(uid)
                if len(collected) >= count:
                    break
        time.sleep(0.5)
    return collected
