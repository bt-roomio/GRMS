from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.views.permissions import PermissionsListView
from users.views.reset_password import ActivationLinkView, ResetPasswordView
from users.views.roles import RoleDetailView, RolesListView
from users.views.send_link import SendLinkView
from users.views.users import UserDetailView, UserListView

urlpatterns = [
    # User-related views
    path("users/", UserListView.as_view(), name="users-list"),
    path("user/<uuid:pk>/", UserDetailView.as_view(), name="users-detail"),
    path("permissions/", PermissionsListView.as_view(), name="permissions-list"),
    path("roles/", RolesListView.as_view(), name="roles-list"),
    path("role/<uuid:pk>/", RoleDetailView.as_view(), name="roles-detail"),
    # JWT-related views
    path("access-token/", TokenObtainPairView.as_view(), name="access-token"),
    path("refresh-token/", TokenRefreshView.as_view(), name="refresh-token"),
    # Reset password views
    path("activation-link/<uuid:user_id>/", ActivationLinkView.as_view(), name="activation-link"),
    path("send-link/", SendLinkView.as_view(), name="send-link"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
