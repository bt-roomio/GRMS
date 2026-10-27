from django.db.models import F

from main.models import Room


def room_list(tenant, room_type=None, sort_by=None):
    """``{id, number, type_id, type_name}`` rows for the services room list. Shared by the REST
    view and the WebSocket consumer so both return the same fields and filters."""
    query = Room.objects.by_tenant(tenant)
    if room_type:
        query = query.filter(type_id=room_type)
    query = query.annotate(type_name=F("type__title")).values("id", "number", "type_id", "type_name")
    return query.order_by(sort_by) if sort_by else query
