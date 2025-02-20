from django.db.models import Count, Q

from core.querysets.base_queryset import BaseQuerySet


class GroupQuerySet(BaseQuerySet):
    def list(self, tenant_id, sort_by=None, search_field=None, search_value=None):
        query = (
            self.prefetch_related("group_room", "created_by", "group_public_space")
            .filter(tenant_id=tenant_id)
            .is_active()
        )

        query = query.annotate(count_staff=Count("groupstaff"))

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))

        return query.order_by(*sort_by)

    def is_active(self):
        return self.filter(is_active=True)
