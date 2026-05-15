from core.querysets.base_queryset import BaseQuerySet


class ControllerQuerySet(BaseQuerySet):
    def list(self, tenant, sort_by=None, search_value=None, file_type=None):
        query = self.filter(tenant=tenant)
        query = query.filter(mac_address__icontains=search_value) if search_value else query
        query = query.filter(file__file_type=file_type) if file_type else query

        return query.order_by(*(sort_by or ["-created_at"]))
