from django.db.models.signals import post_save
from django.dispatch import receiver
from mews.utils.publish_mur_relay import publish_mur_relay_to_mews

from shuttle.models import TsKvLatest


@receiver(post_save, sender=TsKvLatest)
def tskv_latest_signal_handler(sender: TsKvLatest, instance: TsKvLatest, **kwargs):
    publish_mur_relay_to_mews(instance)
