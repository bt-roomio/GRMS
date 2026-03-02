from admin_panel.views.impersonate import ImpersonateView
from admin_panel.views.tenants import AdminTenantListView
from admin_panel.views.users import AdminTenantUsersView
from django.urls import path

urlpatterns = [
    path("tenants/", AdminTenantListView.as_view(), name="admin-tenant-list"),
    path("tenants/<uuid:tenant_id>/users/", AdminTenantUsersView.as_view(), name="admin-tenant-users"),
    path("impersonate/<uuid:user_id>/", ImpersonateView.as_view(), name="admin-impersonate"),
]
