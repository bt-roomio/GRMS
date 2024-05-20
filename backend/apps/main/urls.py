from django.urls import path

from main.views.email_config import EmailConfigDetailView
from main.views.general_settings import GeneralSettingsDetailView
from main.views.room import RoomDetailView, RoomListView

urlpatterns = [
    path("email-config/", EmailConfigDetailView.as_view(), name="email-config-detail"),
    path("general-settings/", GeneralSettingsDetailView.as_view(), name="general-settings-detail"),
    path("room/", RoomListView.as_view(), name="room-list"),
    path("room/<uuid:pk>", RoomDetailView.as_view(), name="room-detail"),
]
