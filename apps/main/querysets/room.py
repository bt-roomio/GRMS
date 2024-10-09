import datetime

from django.db.models import Q, Count, Case, When, Value, F

from core.querysets.base_queryset import BaseQuerySet


class RoomQuerySet(BaseQuerySet):
    def list(self, tenant, state=None, status=None, search_field=None, search_value=None, sort_by=None):
        query = self.filter(active=True)
        query = query.filter(state=state, tenant=tenant) if state else query

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__startswith": search_value}))

        if sort_by:
            for item in sort_by:
                if item in ["number", "-number"]:
                    query = query.order_by(item)
                    continue
                dash = "-" if item.startswith("-") else ""
                item = item.replace("-", "")
                try:
                    query = query.extra(
                        select={f"{item}_as_int": f"CAST(substring({item} FROM '^[0-9]+') AS INTEGER)"}
                    ).order_by(f"{dash}{item}_as_int")
                except Exception:
                    pass
        query = query.filter(status=status) if status else query

        return query

    def room_status(self, tenant):
        query = self.filter(active=True, tenant=tenant)
        today_midnight = datetime.datetime.combine(datetime.date.today(), datetime.time.min).timestamp()
        yesterday_midnight = today_midnight - 86400

        query = (
            query.annotate(
                today=Count(Case(When(updated_at__gte=today_midnight, then=Value(1)))),
                yesterday=Count(
                    Case(When(updated_at__gte=yesterday_midnight, updated_at__lt=today_midnight, then=Value(1)))
                ),
                last_24_hour=Count("state"),
            )
            .values("state", "last_24_hour")
            .annotate(diff_previous_day=F("today") - F("yesterday"), status=F("state"))
        )
        return query
