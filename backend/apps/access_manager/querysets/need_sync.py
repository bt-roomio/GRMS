from core.querysets.base_queryset import BaseQuerySet


class NeedSyncDeviceQuerySet(BaseQuerySet):
    def by_device(self, device):
        return self.filter(device=device)

    def list(self, sort_by):
        return self.order_by(*sort_by)

    def check_avialibility(self, tenant_id, device_ids=None, ids=None):
        queryset = self.filter(need_sync=True, device__tenant_id=tenant_id)

        if ids:
            queryset = queryset.filter(id__in=ids)
        elif device_ids:
            queryset = queryset.filter(device_id__in=device_ids)

        return queryset.exists()
