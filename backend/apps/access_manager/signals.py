from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from access_manager.models import Card, Group, GuestCard, NeedSyncDevice, StaffCard


def _notify_on_commit(*groups: str):
    """Refresh the tenant's live card lists for subscribers after commit.

    Before commit the consumer would re-read stale data; groups are per tenant,
    otherwise a card change in one hotel triggered queries for subscribers of every hotel.
    """

    def send():
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        for group in groups:
            async_to_sync(channel_layer.group_send)(group, {"type": "get_list_activity"})

    transaction.on_commit(send)


def _card_tenant_id(instance):
    # Don't load the whole card: only tenant_id is needed.
    if type(instance).card.is_cached(instance):
        return instance.card.tenant_id
    return Card.objects.filter(pk=instance.card_id).values_list("tenant_id", flat=True).first()


@receiver(post_save, sender=GuestCard)
def guest_card_signal_handler(sender, instance, **kwargs):
    tenant_id = _card_tenant_id(instance)
    _notify_on_commit(f"guest_cards_{tenant_id}", f"cards_{tenant_id}")


@receiver(post_save, sender=StaffCard)
def staff_card_signal_handler(sender, instance, **kwargs):
    _notify_on_commit(f"cards_{_card_tenant_id(instance)}")


@receiver(post_save, sender=Group)
def group_signal_handler(sender, instance, **kwargs):
    _notify_on_commit(f"cards_{instance.tenant_id}")


@receiver(post_save, sender=NeedSyncDevice)
def need_sync_signal_handler(sender, instance, **kwargs):
    card = instance.card
    if not card.is_active:
        card.is_active = True
        card.save()
