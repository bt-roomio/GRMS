from typing import List

from access_manager.models import Card
from access_manager.tasks.send_rpc import send_rpc_request


def dispatch_card_rpc(device_id, cards: List[str], access, **kwargs) -> dict:
    """Send a mixed list of RFID cards and PINs to a device.

    RFID cards go out in one `writeRFID` request; each PIN (`Card.is_pwd`) is sent
    on its own, since the `add_pwd`/`delete_pwd` RPC carries a single password.
    Use this instead of `send_rpc_request` whenever `cards` may contain PINs.
    """
    from main.models import Device

    tenant_id = Device.objects.filter(id=device_id).values_list("tenant_id", flat=True).first()
    pwd_numbers = set(
        Card.objects.filter(tenant_id=tenant_id, number__in=cards, is_pwd=True).values_list("number", flat=True)
    )
    rfid_cards = [card for card in cards if card not in pwd_numbers]
    pins = [card for card in cards if card in pwd_numbers]

    results = []
    if rfid_cards or not pins:
        results.append(send_rpc_request(str(device_id), rfid_cards, access, **kwargs))
    for pin in pins:
        results.append(send_rpc_request(str(device_id), [pin], access, is_pwd=True, **kwargs))

    if len(results) == 1:
        return results[0]

    failed = [result for result in results if not result.get("success")]
    merged = dict(failed[0] if failed else results[0])
    merged.update(
        {
            "success": not failed,
            "message": "; ".join(result.get("message", "") for result in (failed or results)),
            "results": results,
        }
    )
    return merged
