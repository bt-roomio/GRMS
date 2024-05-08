from django.urls import path

from main.views.email_config import EmailConfigDetailView
from main.views.general_settings import GeneralSettingsDetailView

urlpatterns = [
    path('email-config/', EmailConfigDetailView.as_view(), name='email-config-detail'),
    path('general-settings/', GeneralSettingsDetailView.as_view(), name='general-settings-detail'),
]
