from typing import List

MAX_CARDS_PER_REQUEST = 10


def batch_cards(cards: List[str], batch_size: int = MAX_CARDS_PER_REQUEST) -> List[List[str]]:
    return [cards[i : i + batch_size] for i in range(0, len(cards), batch_size)]


def is_same_request(request1: dict, request2: dict) -> bool:
    def remove_id_from_dict(d):
        if isinstance(d, dict):
            return {k: remove_id_from_dict(v) for k, v in d.items() if k != "id"}
        elif isinstance(d, list):
            return [remove_id_from_dict(item) for item in d]
        else:
            return d

    try:
        req1_no_id = remove_id_from_dict(request1)
        req2_no_id = remove_id_from_dict(request2)

        return req1_no_id == req2_no_id

    except Exception:
        return False
