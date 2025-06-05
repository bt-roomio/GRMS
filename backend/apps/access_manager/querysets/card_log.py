from core.querysets.base_queryset import BaseQuerySet


class CardLogQuerySet(BaseQuerySet):
    def by_device(self, device):
        return self.filter(device=device)

    def list(self, sort_by, filters):
        query = self.filter(event_ts__range=(filters.get("from_date"), filters.get('to_date'))) if filters.get(
            "from_date") and filters.get('to_date') else self
        query = query.order_by(*(sort_by))
        return query
