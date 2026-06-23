from django.db.models import Exists, OuterRef, Q

from core.querysets.base_queryset import BaseQuerySet


class CardQuerySet(BaseQuerySet):
    def list(
        self, tenant_id, sort_by=None, search_field=None, search_value=None, filters={}, staff_id=None, is_pwd=None
    ):
        from access_manager.models import GuestCard, NeedSyncDevice, StaffCard

        query = self.select_related("created_by").filter(tenant_id=tenant_id)

        if staff_id:
            query = query.filter(id__in=StaffCard.objects.filter(staff_id=staff_id, is_active=True).values("card_id"))

        if is_pwd is not None:
            query = query.filter(is_pwd=is_pwd)

        if "need_sync" in filters:
            need_sync = filters.get("need_sync")
            query = query.annotate(need_sync=Exists(NeedSyncDevice.objects.filter(card=OuterRef("pk"), need_sync=True)))
            query = query.filter(need_sync=need_sync)

        if "active" in filters:
            has_holder = Exists(StaffCard.objects.filter(card=OuterRef("pk"), is_active=True)) | Exists(
                GuestCard.objects.filter(card=OuterRef("pk"), is_active=True)
            )
            query = query.filter(has_holder if filters.get("active") else ~has_holder)

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        return query.order_by(*sort_by)
