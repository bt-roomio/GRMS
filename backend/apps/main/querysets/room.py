import logging

from access_manager.tasks.send_rpc import send_rpc_request
from django.db.models import (
    Aggregate,
    Case,
    Count,
    F,
    Func,
    IntegerField,
    JSONField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    TextField,
    Value,
    When,
)
from django.db.models.functions import Cast, Coalesce

from core.querysets.base_queryset import BaseQuerySet
from core.utils.helpers import safely_remove
from shuttle.models import AttributeKv, TsKvDictionary, TsKvLatest

logger = logging.getLogger(__name__)


class JSONBObjectAgg(Aggregate):
    """
    Wraps the Postgres jsonb_object_agg(key_field, value_field) aggregate.
    Produces a JSONB object of the form { key_field: value_field, … }.
    """

    function = "jsonb_object_agg"
    name = "JSONB_OBJECT_AGG"
    output_field = JSONField()  # pyright: ignore


class RoomQuerySet(BaseQuerySet):
    def list(self, tenant, state=None, status=None, search_field=None, search_value=None, sort_by=None, blocks=None):
        query = self.filter(active=True, tenant=tenant)
        query = query.prefetch_related("devices__ts_kvs_latest__key", "type")
        query = query.annotate(
            count_online_devices=Count("devices", filter=Q(Q(devices__status=True) & Q(devices__is_active=True)))
        )
        query = query.annotate(count_devices=Count("devices", filter=Q(devices__is_active=True)))
        query = query.filter(state__contains=[state]) if state is not None and state not in [2, 3, 4] else query
        query = query.filter(id__in=get_occupied_rooms(tenant)) if state == 2 else query
        query = query.filter(id__in=get_dnd_rooms(tenant)) if state == 3 else query
        query = query.filter(id__in=get_mur_rooms(tenant)) if state == 4 else query
        if blocks:
            blocks_filter = Q()
            for block, floors in blocks.items():
                blocks_filter |= Q(block=block, floor__in=floors)
            query = query.filter(blocks_filter)

        if search_field and search_value:
            search_filter = Q(**{f"{search_field}__istartswith": search_value})

            if search_field.startswith("devices__"):
                door_lock_field = search_field.replace("devices__", "door_lock_device__")
                search_filter = Q(**{f"{search_field}__istartswith": search_value, "devices__is_active": True}) | Q(
                    **{f"{door_lock_field}__istartswith": search_value, "door_lock_device__is_active": True}
                )
            query = query.filter(search_filter)

        if status == "ON":
            query = query.filter(count_online_devices=F("count_devices"), count_devices__gt=0)
        elif status == "OFF":
            query = query.exclude(count_online_devices=F("count_devices"), count_devices__gt=0)
        return query.order_by(*(sort_by or ["block", "floor", "number"]) + ["id"])

    def quick_list(self, tenant, search_field=None, search_value=None, sort_by=None):
        query = self.filter(active=True, tenant=tenant)
        if search_field and search_value:
            search_filter = Q(**{f"{search_field}__istartswith": search_value})

            if search_field.startswith("devices__"):
                door_lock_field = search_field.replace("devices__", "door_lock_device__")
                search_filter = Q(**{f"{search_field}__istartswith": search_value, "devices__is_active": True}) | Q(
                    **{f"{door_lock_field}__istartswith": search_value, "door_lock_device__is_active": True}
                )
            query = query.filter(search_filter)
        elif search_value:
            query = query.filter(
                Q(number__istartswith=search_value) | Q(floor__istartswith=search_value) | Q(block__istartswith=search_value)
            )

        return query.order_by(*(sort_by or ["block", "floor", "number"]) + ["id"])

    def guest_details(self, tenant):
        from main.models import Guest

        return self.prefetch_related(
            Prefetch(
                "guests",
                queryset=Guest.objects.filter(is_active=True).order_by("-created_at"),
                to_attr="prefetched_guests",
            )
        )

    def rooms_ts_kvs(self, tenant, keys):
        from shuttle.models import TsKvLatest

        if not keys or (keys and not isinstance(keys, list)):
            logger.warning("rooms_ts_kvs: keys parameter is missing or not a list")
            return self

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

    def get_tags(self, tenant, tags):
        from main.models import Device

        if not tags or (tags and not isinstance(tags, list)):
            return self

        query = self.filter(active=True, tenant=tenant)
        attrs_filters = Q()
        # ts_kvs_keys = [*STATIC_KEYS.values()]
        ts_kvs_keys = []
        for tag in tags:
            if tag.get("tag_type") == "attribute":
                attrs_filters |= Q(attribute_key=tag["name"], attribute_type=tag["attribute_scope"])
            else:
                ts_kvs_keys.append(tag["name"])

        if not attrs_filters.children:
            attrs_filters = Q(pk__in=[])

        query = query.prefetch_related(
            Prefetch(
                "devices",
                queryset=Device.objects.annotate(
                    priority=Case(
                        When(additional_info__primary=True, then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField(),
                    )
                )
                .order_by("priority", "created_at")
                .prefetch_related(
                    Prefetch(
                        "attribute_kvs",
                        queryset=AttributeKv.objects.filter(attrs_filters).annotate(
                            value=Coalesce(
                                Cast("bool_v", TextField()),
                                Cast("str_v", TextField()),
                                Cast("dbl_v", TextField()),
                                Cast("long_v", TextField()),
                                Cast("json_v", TextField()),
                                output_field=TextField(),
                            )
                        ),
                        to_attr="attrs",
                    ),
                    Prefetch(
                        "attribute_kvs",
                        queryset=TsKvLatest.objects.prefetch_related("key")
                        .filter(key__key__in=ts_kvs_keys)
                        .annotate(
                            value=Coalesce(
                                Cast("bool_v", TextField()),
                                Cast("str_v", TextField()),
                                Cast("dbl_v", TextField()),
                                Cast("long_v", TextField()),
                                Cast("json_v", TextField()),
                                output_field=TextField(),
                            )
                        ),
                        to_attr="ts_kvs",
                    ),
                ),
                to_attr="room_devices",
            )
        )

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
        from main.models import Guest, Room
        from main.utils.access_context import get_guest_access_context

        deactivate_result = {"success": True}
        query = self.filter(id=room_id, state__contains=[Room.CheckedIn])
        guests = Guest.objects.filter(room_id=room_id, is_active=True)
        access_context = get_guest_access_context(guests)
        devices = access_context.get("devices", [])
        cards = access_context.get("cards", [])

        for device in devices:
            result = send_rpc_request(str(device.id), cards, 0, user=user)
            not result.get("success") and deactivate_result.update({"success": False})  # pyright: ignore

        guests.update(is_active=False)
        for room in query:
            room.state = safely_remove(room.state, Room.CheckedIn)
            room.state.append(Room.Available)
            room.save(update_fields=["state"])
        return guests.count(), deactivate_result

    def block_floors(self, tenant):
        query = (
            self.filter(active=True, tenant=tenant)
            .values("block", "floor")
            .annotate(count=Count("id"))
            .order_by("block", "floor")
        )

        blocks: dict = {}
        for item in query:
            block = item["block"]
            floor = item["floor"]
            count = item["count"]

            if block not in blocks:
                blocks[block] = {"name": block, "count": 0, "floors": []}

            blocks[block]["count"] += count
            blocks[block]["floors"].append({"name": floor, "count": count})

        return list(blocks.values())

    def total_rooms_count(self, tenant_id):
        return self.filter(active=True, tenant_id=tenant_id).count()

    def checked_in_count(self, tenant_id):
        from main.models import Room

        return self.filter(active=True, tenant_id=tenant_id, state__contains=[Room.CheckedIn]).count()

    def available_count(self, tenant_id):
        from main.models import Room

        return self.filter(active=True, tenant_id=tenant_id, state__contains=[Room.Available]).count()


def get_dnd_rooms(tenant):
    key_dict = TsKvDictionary.objects.filter(key="DND Relay").first()
    if key_dict is not None:
        return TsKvLatest.objects.filter(
            long_v=1,
            entity__tenant=tenant,
            key=key_dict.key_id,
        ).values_list("entity__room_id", flat=True)
    return []


def get_mur_rooms(tenant):
    key_dict = TsKvDictionary.objects.filter(key="MUR Relay").first()
    if key_dict is not None:
        return TsKvLatest.objects.filter(
            long_v=1,
            entity__tenant=tenant,
            key=key_dict.key_id,
        ).values_list("entity__room_id", flat=True)
    return []


def get_occupied_rooms(tenant):
    return TsKvLatest.objects.filter(
        long_v=1,
        entity__tenant=tenant,
        key__key="Occupancy State",
    ).values_list("entity__room_id", flat=True)
