from core.querysets.base_queryset import BaseQuerySet
from django.db.models import Q


class RoomQuerySet(BaseQuerySet):
    def list(self, tenant, state=None, status=None, search_field=None, search_value=None, sort_by=None):
        query = self.filter(active=True)
        query = query.filter(state=state, tenant=tenant) if state else query

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__startswith": search_value}))

        if sort_by:
            for item in sort_by:
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
