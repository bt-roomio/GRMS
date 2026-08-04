from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from fleet.models import FleetNode
from fleet.observables.fleet_node import publish_fleet_nodes


@receiver([post_save, post_delete], sender=FleetNode)
def fleet_node_changed(instance: FleetNode, **kwargs):
    publish_fleet_nodes([instance.tenant_id])
