from django.db.models import Exists, OuterRef

from core.querysets.base_queryset import BaseQuerySet


class GuestCardQuerySet(BaseQuerySet):
    def list(self, tenant_id, room=None, sort_by=[], filters={}):
        from access_manager.models import NeedSyncDevice
        need_sync = filters.get("need_sync")

        query = self.filter(guest__tenant_id=tenant_id, is_active=True)
        query = query.filter(guest__room=room) if room else query
        query = query.annotate(
            need_sync=Exists(
                NeedSyncDevice.objects.filter(
                    card=OuterRef('card'),
                    need_sync=True
                )
            )
        )
        query = query.filter(need_sync=need_sync) if need_sync is not None else query

        return query.order_by(*sort_by)
