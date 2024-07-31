from django.urls import path

from main.views.alarm_settings import AlarmSettingsDetailView
from main.views.dashboard import DashboardDetailView, DashboardListView
from main.views.device import DeviceListView
from main.views.device_credentials import DeviceCredentialsDetailView
from main.views.email_config import EmailConfigDetailView
from main.views.general_settings import GeneralSettingsDetailView
from main.views.guest import GuestListView, GuestDetailView
from main.views.guest_move_room import GuestMoveRoomListView
from main.views.room import RoomDetailView, RoomListView
from main.views.room_type import RoomTypeDetailView, RoomTypeListView
from main.views.widget_type import WidgetTypeDetailView, WidgetTypeListView

urlpatterns = [
    path("email-config/", EmailConfigDetailView.as_view(), name="email-config-detail"),
    path("general-settings/", GeneralSettingsDetailView.as_view(), name="general-settings-detail"),
    path("alarm-settings/", AlarmSettingsDetailView.as_view(), name="alarm-settings"),
    path("room/", RoomListView.as_view(), name="room-list"),
    path("room/<uuid:pk>", RoomDetailView.as_view(), name="room-detail"),
    path("room-type/", RoomTypeListView.as_view(), name="room-type-list"),
    path("room-type/<uuid:pk>", RoomTypeDetailView.as_view(), name="room-type-detail"),
    path("widget-type/", WidgetTypeListView.as_view(), name="widget-type-list"),
    path("widget-type/<uuid:pk>", WidgetTypeDetailView.as_view(), name="widget-type-detail"),
    path("dashboard/", DashboardListView.as_view(), name="dashboard-list"),
    path("dashboard/<uuid:pk>", DashboardDetailView.as_view(), name="dashboard-detail"),
    path("device/", DeviceListView.as_view(), name="device-list"),
    path("device/<str:token>/credentials/", DeviceCredentialsDetailView.as_view(), name="device-credentials-detail"),
    path("guest/", GuestListView.as_view(), name="guest-list"),
    path("guest/move/room/", GuestMoveRoomListView.as_view(), name="guest-move-room-list"),
    path("guest/<uuid:pk>/", GuestDetailView.as_view(), name="guest-detail"),
]
