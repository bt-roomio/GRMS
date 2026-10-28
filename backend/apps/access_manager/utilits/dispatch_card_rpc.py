from typing import List

from access_manager.models import Card
from access_manager.tasks.send_rpc import send_rpc_request
from access_manager.utilits.merge_rpc_results import merge_rpc_results


def dispatch_card_rpc(device_id, cards: List[str], access, is_pwd=False, **kwargs) -> dict:
    """Send a mixed list of RFID cards and PINs to a device and merge the results.

    - Default-profile devices take all RFID cards in one `writeRFID` request.
    - Other devices get one request per RFID card.
    - Each PIN (`Card.is_pwd`, or every card when `is_pwd=True`) is sent on its own,
      since the `add_pwd`/`delete_pwd` RPC carries a single password.

    Use this instead of `send_rpc_request` whenever `cards` may hold several cards or PINs;
    `kwargs` are passed through to every request.
    """
    from main.models import Device

    device = Device.objects.select_related("device_profile").filter(id=device_id).first()
    is_default = bool(device and device.device_profile and device.device_profile.name.lower() == "default")

    if is_pwd:
        pwd_numbers = set(cards)
    else:
        pwd_numbers = set(
            Card.objects.filter(tenant_id=device and device.tenant_id, number__in=cards, is_pwd=True).values_list(
                "number", flat=True
            )
        )
    rfid_cards = [card for card in cards if card not in pwd_numbers]
    pins = [card for card in cards if card in pwd_numbers]

    batches = [(rfid_cards, False)] if is_default and rfid_cards else [([card], False) for card in rfid_cards]
    batches += [([pin], True) for pin in pins]

    batches = batches or [([], False)]

    results = [send_rpc_request(str(device_id), batch, access, is_pwd=pwd, **kwargs) for batch, pwd in batches]
    return merge_rpc_results(results)
