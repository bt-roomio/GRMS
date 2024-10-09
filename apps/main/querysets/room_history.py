from datetime import datetime, timedelta

from django.db.models import Case, When, Value, F, Count

from core.querysets.base_queryset import BaseQuerySet


class RoomHistoryQuerySet(BaseQuerySet):
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
