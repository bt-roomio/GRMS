from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class GlobalSettingsTemplateQuerySet(BaseQuerySet):
    def list(self, sort_by=None, search_field=None, search_value=None):
        query = self
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__icontains": search_value}))

        return query.order_by(*sort_by) if sort_by else query.order_by("-created_at")
