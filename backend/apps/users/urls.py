from django.urls import path

from users.views.auth import callback_provider
from users.views.dashboards import (
    MyDashboardsOrderView,
    MyDashboardsView,
    UserDashboardDetailView,
    UserDashboardListView,
)
from users.views.jwt_token import CustomTokenObtainPairView, CustomTokenRefreshView
from users.views.keycloak import kc_begin, kc_callback, kc_logout
from users.views.permissions import PermissionsListView
from users.views.reset_password import ActivationLinkView, ResetPasswordView
from users.views.roles import RoleDetailView, RolesListView
from users.views.send_link import SendLinkView
from users.views.users import UserDetailView, UserListView

urlpatterns = [
    # Keycloak
    path("auth/keycloak/begin/", kc_begin, name="kc_begin"),
    path("auth/keycloak/callback/", kc_callback, name="kc_callback"),
    path("auth/keycloak/logout/", kc_logout, name="kc_logout"),
    # User-related views
    path("users/", UserListView.as_view(), name="users-list"),
    path("user/<uuid:pk>/", UserDetailView.as_view(), name="users-detail"),
    path("permissions/", PermissionsListView.as_view(), name="permissions-list"),
    path("roles/", RolesListView.as_view(), name="roles-list"),
    path("role/<uuid:pk>/", RoleDetailView.as_view(), name="roles-detail"),
    path("dashboards/", UserDashboardListView.as_view(), name="dashboards-list"),
    path("dashboard/<uuid:pk>/", UserDashboardDetailView.as_view(), name="dashboards-detail"),
    path("me/dashboards/", MyDashboardsView.as_view(), name="my-dashboards"),
    path("me/dashboards/order/", MyDashboardsOrderView.as_view(), name="my-dashboards-order"),
    # JWT-related views
    path("access-token/", CustomTokenObtainPairView.as_view(), name="access-token"),
    path("refresh-token/", CustomTokenRefreshView.as_view(), name="refresh-token"),  # Reset password views
    path("callback/", callback_provider, name="callback"),
    path("activation-link/<uuid:user_id>/", ActivationLinkView.as_view(), name="activation-link"),
    path("send-link/", SendLinkView.as_view(), name="send-link"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
