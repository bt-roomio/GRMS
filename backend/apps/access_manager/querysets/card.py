from django.db.models import Q, Exists, OuterRef

from core.querysets.base_queryset import BaseQuerySet


class CardQuerySet(BaseQuerySet):
    def list(self, tenant_id, sort_by=None, search_field=None, search_value=None, filters={}):
        from access_manager.models import NeedSyncDevice

        query = self.select_related("created_by").filter(tenant_id=tenant_id)
        if 'need_sync' in filters:
            need_sync = filters.get("need_sync")
            query = query.annotate(
                need_sync=Exists(
                    NeedSyncDevice.objects.filter(
                        card=OuterRef('pk'),
                        need_sync=True
                    )
                )
            )
            query = query.filter(need_sync=need_sync)

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        return query.order_by(*sort_by)
