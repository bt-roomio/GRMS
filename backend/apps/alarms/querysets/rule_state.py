from core.querysets.base_queryset import BaseQuerySet


class AlarmRuleStateQuerySet(BaseQuerySet):
    def for_devices(self, device_ids):
        return self.filter(device_id__in=device_ids)
