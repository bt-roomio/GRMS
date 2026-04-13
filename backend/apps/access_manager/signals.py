from access_manager.models import Group, GuestCard, NeedSyncDevice, StaffCard
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=GuestCard)
def tskv_signal_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)("guest_cards", {"type": "get_list_activity"})


@receiver(post_save, sender=GuestCard)
def guest_card_signal_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)("cards", {"type": "get_list_activity"})


@receiver(post_save, sender=StaffCard)
def staff_card_signal_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)("cards", {"type": "get_list_activity"})


@receiver(post_save, sender=Group)
def group_signal_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)("cards", {"type": "get_list_activity"})


@receiver(post_save, sender=NeedSyncDevice)
def need_sync_signal_handler(sender, instance, **kwargs):
    card = instance.card
    if not card.is_active:
        card.is_active = True
        card.save()
