from celery import shared_task

from access_manager.models import Card, NeedSyncDevice
from access_manager.utilits.unplug_card import disconnect_guests, disconnect_staff


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def unplug(card_id):
    """Remove the card from every device synchronously, then deactivate it. """
    card = Card.objects.filter(id=card_id).first()
    if not card:
        return False

    card_num = str(card.number)

    disconnect_staff(card, card_num)
    disconnect_guests(card, card_num)

    if NeedSyncDevice.objects.filter(card=card, need_sync=True).exists():
        return False

    Card.objects.filter(id=card.id).update(is_active=False)
    return True
