import datetime

from django.db.models import Count, Func

from core.querysets.base_queryset import BaseQuerySet


class RoomHistoryQuerySet(BaseQuerySet):
    def yesterday_statuses(self, tenant):
        from main.models import Room

        query = self.filter(tenant=tenant)

        today_midnight = datetime.datetime.combine(datetime.date.today(), datetime.time.min).timestamp()
        yesterday_midnight = today_midnight - 86400

        query = query.filter(created_at__gte=yesterday_midnight, created_at__lt=today_midnight)

        rooms_states = (
            query.annotate(state_element=Func("state", function="unnest"))
            .values("state_element")
            .annotate(count=Count("id"))
            .order_by("state_element")
        )

        result = []
        for s in rooms_states:
            data = {"status": Room.STATE[s["state_element"]][1], "yesterday": s["count"]}
            result.append(data)

        return result
