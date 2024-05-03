from django.urls import path

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.views.reset_password import GetResetLinkView, ResetPasswordView
from users.views.users import UserDetailView

urlpatterns = [
    path('user/', UserDetailView.as_view(), name='user-detail-view'),
    path('access-token/', TokenObtainPairView.as_view(), name='access-token'),
    path('refresh-token/', TokenRefreshView.as_view(), name='refresh-token'),
    path('reset-link/', GetResetLinkView.as_view(), name='reset-link'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
]
