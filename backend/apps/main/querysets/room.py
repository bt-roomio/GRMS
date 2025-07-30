from access_manager.models import GuestCard
from access_manager.tasks.send_rpc import send_rpc_request
from django.db.models import Aggregate, Count, F, Func, JSONField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from core.querysets.base_queryset import BaseQuerySet
from core.utils.helpers import safely_remove
from shuttle.models import TsKvDictionary, TsKvLatest


class JSONBObjectAgg(Aggregate):
    """
    Wraps the Postgres jsonb_object_agg(key_field, value_field) aggregate.
    Produces a JSONB object of the form { key_field: value_field, … }.
    """

    function = "jsonb_object_agg"
    name = "JSONB_OBJECT_AGG"
    output_field = JSONField()  # pyright: ignore


class RoomQuerySet(BaseQuerySet):
    def list(self, tenant, state=None, status=None, search_field=None, search_value=None, sort_by=None):
        query = self.filter(active=True, tenant=tenant)
        query = query.prefetch_related("devices__ts_kvs_latest__key", "type")
        query = query.annotate(
            count_online_devices=Count("devices", filter=Q(Q(devices__status=True) & Q(devices__is_active=True)))
        )
        query = query.annotate(count_devices=Count("devices", filter=Q(devices__is_active=True)))
        query = query.filter(state__contains=[state]) if state and state not in [2, 3, 4] else query
        query = query.filter(id__in=get_occupied_rooms(tenant)) if state == 2 else query
        query = query.filter(id__in=get_dnd_rooms(tenant)) if state == 3 else query
        query = query.filter(id__in=get_mur_rooms(tenant)) if state == 4 else query

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        query = query.filter(status=status) if status else query
        return query.order_by(*(sort_by or ["number"]) + ["id"])

    def rooms_ts_kvs(self, tenant, keys=[]):
        query = self.filter(active=True, tenant=tenant)

        tskv_grouped = (
            TsKvLatest.objects.filter(entity__room=OuterRef("pk"), key__key__in=keys)
            .values("entity__room")
            .annotate(
                mapped=JSONBObjectAgg(
                    "key__key",
                    Coalesce(
                        Func(F("str_v"), function="to_jsonb", output_field=JSONField()),
                        Func(F("long_v"), function="to_jsonb", output_field=JSONField()),
                        Func(F("bool_v"), function="to_jsonb", output_field=JSONField()),
                        F("json_v"),
                        Func(F("dbl_v"), function="to_jsonb", output_field=JSONField()),
                        output_field=JSONField(),
                    ),
                )
            )
            .values("mapped")
        )
        query = query.annotate(ts_kv_values=Subquery(tskv_grouped))

        return query

    def statuses(self, tenant):
        from main.models import Room

        query = self.filter(active=True, tenant=tenant)

        rooms_states = (
            query.annotate(state_element=Func("state", function="unnest"))
            .values("state_element")
            .annotate(count=Count("id"))
            .order_by("state_element")
        )

        result = []
        for s in rooms_states:
            data = {"status": Room.STATE[s["state_element"]][1], "today": s["count"]}
            result.append(data)

        return result

    def guest_checkout(self, room_id, user=None):
        from main.models import Device, Guest, Room

        deactivate_result = {"success": True}
        query = self.filter(id=room_id, state__contains=[Room.CheckedIn])
        guests = Guest.objects.filter(room_id=room_id, is_active=True)
        cards = list(GuestCard.objects.filter(guest__in=guests, is_active=True).values_list("card__number", flat=True))
        devices = Device.objects.filter(
            Q(room__id=room_id)
            | Q(device_public_spaces__public_space__room_type_public_spaces__room_type__room__guests__in=guests),
            is_active=True,
        ).distinct()
        for device in devices:
            result = send_rpc_request(str(device.id), cards, 0, user=user)
            not result.get("success") and deactivate_result.update({"success": False})

        guests.update(is_active=False)
        for room in query:
            room.state = safely_remove(room.state, Room.CheckedIn)
            room.state.append(Room.Available)
            room.save(update_fields=["state"])
        return guests.count(), deactivate_result


def get_dnd_rooms(tenant):
    key_dict = TsKvDictionary.objects.filter(key="DND Relay").first()
    if key_dict is not None:
        return TsKvLatest.objects.filter(
            long_v=1,
            entity__tenant=tenant,
            key=key_dict.key_id,
        ).values_list("entity__room_id", flat=True)


def get_mur_rooms(tenant):
    key_dict = TsKvDictionary.objects.filter(key="MUR Relay").first()
    if key_dict is not None:
        return TsKvLatest.objects.filter(
            long_v=1,
            entity__tenant=tenant,
            key=key_dict.key_id,
        ).values_list("entity__room_id", flat=True)


def get_occupied_rooms(tenant):
    return TsKvLatest.objects.filter(
        long_v=1,
        entity__tenant=tenant,
        key__key="Occupancy State",
    ).values_list("entity__room_id", flat=True)
