import datetime

from django.db.models import Count, F, Func, Q

from core.querysets.base_queryset import BaseQuerySet
from shuttle.models import TsKvDictionary, TsKvLatest


class RoomQuerySet(BaseQuerySet):
    def list(self, tenant, state=None, status=None, search_field=None, search_value=None, sort_by=None):
        query = self.filter(active=True, tenant=tenant)
        query = query.prefetch_related("devices", "type")
        query = query.annotate(count_online_devices=Count("devices", filter=Q(devices__status=True)))
        query = query.annotate(count_devices=Count("devices"))
        query = query.filter(state__contains=[state]) if state and state not in [3, 4] else query
        query = query.filter(id__in=get_dnd_rooms(tenant)) if state == 3 else query
        query = query.filter(id__in=get_mur_rooms(tenant)) if state == 4 else query

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        query = query.filter(status=status) if status else query

        return query.order_by(*sort_by or ["number"])

    def room_status(self, tenant):
        from main.models import Room

        query = self.filter(active=True, tenant=tenant)
        today_midnight = datetime.datetime.combine(datetime.date.today(), datetime.time.min).timestamp()
        yesterday_midnight = today_midnight - 86400

        rooms_updated_today = (
            query.filter(updated_at__gte=today_midnight)
            .annotate(state_element=Func("state", function="unnest"))
            .values("state_element")
            .annotate(count_today=Count("id"))
        )

        rooms_updated_yesterday = (
            query.filter(updated_at__gte=yesterday_midnight, updated_at__lt=today_midnight)
            .annotate(state_element=Func("state", function="unnest"))
            .values("state_element")
            .annotate(count_yesterday=Count("id"))
        )

        today_counts = {room["state_element"]: room["count_today"] for room in rooms_updated_today}
        yesterday_counts = {room["state_element"]: room["count_yesterday"] for room in rooms_updated_yesterday}

        all_states_tenant = (
            query.annotate(state_element=Func("state", function="unnest"))
            .values("state_element")
            .annotate(count=Count("id"))
            .order_by("state_element")
        )
        result = []
        for s in all_states_tenant:
            data = {"status": Room.STATE[s["state_element"]][1], "last_24_hour": s["count"], "diff_previous_day": 0}
            result.append(data)

        all_state_elements = set(today_counts.keys()).union(yesterday_counts.keys())
        for state_element in all_state_elements:
            count_today = today_counts.get(state_element, 0)
            count_yesterday = yesterday_counts.get(state_element, 0)
            difference = count_today - count_yesterday
            for elem in result:
                if elem["status"] == Room.STATE[state_element][1]:
                    elem["diff_previous_day"] = difference

        return result

    def guest_checkout(self, room_id):
        from main.models import Guest, Room

        query = self.filter(id=room_id, state__contains=[Room.CheckedIn])
        guests = Guest.objects.filter(room_id=room_id, is_active=True).update(is_active=False)
        query.update(state=Func(F("state"), Room.CheckedIn, function="array_remove"))
        return guests


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
