from datetime import datetime, timedelta

from django.db.models import Case, When, Value, F, Q, Count

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
        now = datetime.now()
        last_24h = now - timedelta(seconds=86400)
        prev_24h = now - timedelta(seconds=86400 * 2)

        last_24h_timestamp = int(last_24h.timestamp())
        prev_24h_timestamp = int(prev_24h.timestamp())

        query = (
            query.annotate(
                last_day=Count(Case(When(created_at__gte=last_24h_timestamp, then=Value(1)))),
                previous_day=Count(
                    Case(When(created_at__gte=prev_24h_timestamp, created_at__lt=last_24h, then=Value(1)))
                ),
            )
            .values("state")
            .annotate(
                last_24_hour=F("last_day"), diff_previous_day=F("last_day") - F("previous_day"), status=F("state")
            )
            .values("status", "last_24_hour", "diff_previous_day")
        )
        return query
