from django.contrib.auth.models import Permission
from django.db.models import Q, QuerySet

from core.utils.constants import UI_PERMISSIONS

# Roles that always hold every permission and UI section, including ones added later
ADMIN_ROLE_NAMES = ("TENANT_ADMIN", "SYS_ADMIN")


class RoleQuerySet(QuerySet):
    def list(self, tenants, unscoped, search_field=None, search_value=None):
        """`tenants` is the caller's scope; `unscoped` lifts it for a plain superuser."""
        query = self.prefetch_related("permissions", "dashboards")
        query = query if unscoped else query.filter(tenant__in=tenants)
        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__istartswith": search_value}))
        elif search_value:
            query = query.filter(Q(name__istartswith=search_value))
        return query

    def quick_list(self, tenant, search_value=None):
        query = self.filter(tenant=tenant)
        if search_value:
            query = query.filter(Q(name__icontains=search_value))
        return query

    def admins(self):
        return self.filter(name__in=ADMIN_ROLE_NAMES)

    def grant_all_permissions(self):
        """Link every existing permission to each role; links already in place are left untouched."""
        permission_ids = list(Permission.objects.values_list("id", flat=True))
        for role in self:
            role.permissions.add(*permission_ids)

    def grant_all_ui_permissions(self):
        """Put the full UI permission list on each role; only roles that lack it are written. Returns that count."""
        changed = []
        for role in self:
            info = role.additional_info if isinstance(role.additional_info, dict) else {}
            if info.get("ui_permissions") != UI_PERMISSIONS:
                role.additional_info = {**info, "ui_permissions": list(UI_PERMISSIONS)}
                changed.append(role)
        if changed:
            self.model.objects.bulk_update(changed, ["additional_info"])
        return len(changed)
