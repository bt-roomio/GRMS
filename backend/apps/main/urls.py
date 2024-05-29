from django.urls import path

from main.views.device import DeviceListView
from main.views.email_config import EmailConfigDetailView
from main.views.general_settings import GeneralSettingsDetailView
from main.views.room import RoomDetailView, RoomListView
from main.views.room_type import RoomTypeListView, RoomTypeDetailView
from main.views.widget_type import WidgetTypeListView

urlpatterns = [
    path("email-config/", EmailConfigDetailView.as_view(), name="email-config-detail"),
    path("general-settings/", GeneralSettingsDetailView.as_view(), name="general-settings-detail"),
    path("room/", RoomListView.as_view(), name="room-list"),
    path("room/<uuid:pk>", RoomDetailView.as_view(), name="room-detail"),
    path("room-type/", RoomTypeListView.as_view(), name="room-type-list"),
    path("room-type/<uuid:pk>", RoomTypeDetailView.as_view(), name="room-type-detail"),
    path("widget-type/", WidgetTypeListView.as_view(), name="widget-type-list"),
    path("device/", DeviceListView.as_view(), name="device-list"),
]
