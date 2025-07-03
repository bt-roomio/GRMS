from core.querysets.base_queryset import BaseQuerySet


class NeedSyncDeviceQuerySet(BaseQuerySet):
    def by_device(self, device):
        return self.filter(device=device)

    def list(self, sort_by):
        return self.order_by(*sort_by)
