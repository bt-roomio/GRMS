from core.querysets.base_queryset import BaseQuerySet


class AlarmCommentQuerySet(BaseQuerySet):
    def for_alarm(self, alarm_id):
        return self.filter(alarm_id=alarm_id).select_related("user")
