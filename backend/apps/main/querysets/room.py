from core.querysets.base_queryset import BaseQuerySet
from django.db.models import Q


class RoomQuerySet(BaseQuerySet):
	def list(self, tenant, state, status=None, search_field=None, search_value=None, sort_by=None):
		query = self.filter(active=True)
		query = query.filter(state=state, tenant=tenant)

		if search_field and search_value:
			query = query.filter(Q(**{f"{search_field}__startswith": search_value}))

		query = query.order_by(*sort_by) if sort_by else query
		query = query.filter(status=status) if status else query
		return query.order_by("room_number")
