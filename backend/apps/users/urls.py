from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from users.views.groups import GroupsListView
from users.views.reset_password import ActivationLinkView, ResetPasswordView
from users.views.users import UserDetailView, UserListView

urlpatterns = [
    # User-related views
    path("users/", UserListView.as_view(), name="users-list"),
    path("user/<uuid:pk>", UserDetailView.as_view(), name="users-detail"),
    path("groups/", GroupsListView.as_view(), name="groups-list"),
    # JWT-related views
    path("access-token/", TokenObtainPairView.as_view(), name="access-token"),
    path("refresh-token/", TokenRefreshView.as_view(), name="refresh-token"),
    # Reset password views
    path("activation-link/<uuid:user_id>/", ActivationLinkView.as_view(), name="activation-link"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
