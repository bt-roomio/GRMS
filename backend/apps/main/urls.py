from django.urls import path

from main.views.change_email_config import ChangeEmailConfig

urlpatterns = [
    path('change-email-config/', ChangeEmailConfig.as_view(), name='change-email-config')
]
