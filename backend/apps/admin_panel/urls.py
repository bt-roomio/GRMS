from admin_panel.views.impersonate import ImpersonateView
from admin_panel.views.integrations import AdminTenantIntegrationDetailView, AdminTenantIntegrationsView
from admin_panel.views.roles import AdminTenantRolesView
from admin_panel.views.tenant_groups import AdminTenantGroupDetailView, AdminTenantGroupListView
from admin_panel.views.tenants import AdminTenantDetailView, AdminTenantListView
from admin_panel.views.users import AdminChangePasswordView, AdminTenantUserDetailView, AdminTenantUsersView
from django.urls import path

urlpatterns = [
    path("tenant/", AdminTenantListView.as_view(), name="admin-tenant-list"),
    path("tenant/<uuid:tenant_id>/", AdminTenantDetailView.as_view(), name="admin-tenant-detail"),
    path("tenant/<uuid:tenant_id>/user/", AdminTenantUsersView.as_view(), name="admin-tenant-users"),
    path(
        "tenant/<uuid:tenant_id>/user/<uuid:user_id>/",
        AdminTenantUserDetailView.as_view(),
        name="admin-tenant-user-detail",
    ),
    path("tenant/<uuid:tenant_id>/role/", AdminTenantRolesView.as_view(), name="admin-tenant-roles"),
    path(
        "tenant/<uuid:tenant_id>/integration/", AdminTenantIntegrationsView.as_view(), name="admin-tenant-integrations"
    ),
    path(
        "tenant/<uuid:tenant_id>/integration/<str:integrator>/",
        AdminTenantIntegrationDetailView.as_view(),
        name="admin-tenant-integration-detail",
    ),
    path("tenant-group/", AdminTenantGroupListView.as_view(), name="admin-group-list"),
    path("tenant-group/<uuid:group_id>/", AdminTenantGroupDetailView.as_view(), name="admin-group-detail"),
    path("user/<uuid:user_id>/change-password/", AdminChangePasswordView.as_view(), name="admin-user-change-password"),
    path("impersonate/<uuid:user_id>/", ImpersonateView.as_view(), name="admin-impersonate"),
]
