from core.querysets.base_queryset import BaseQuerySet


class CardLogQuerySet(BaseQuerySet):
    def by_device(self, device):
        return self.filter(device=device)

    def list(self, filters={}, sort_by=[]):
        query = self
        from_date = filters.get("from_date")
        to_date = filters.get("to_date")

        if from_date:
            query = query.filter(event_ts__gte=from_date)
        if to_date:
            query = query.filter(event_ts__lte=to_date)

        return query.order_by(*sort_by)
