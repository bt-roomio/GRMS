from django.urls import path

from main.views.admin_settings import AdminSettingsView
from main.views.alarm_settings import AlarmSettingsDetailView
from main.views.block_floor import BlockFloorsView
from main.views.dashboard import DashboardDetailView, DashboardListView, DashboardTypeView
from main.views.device import DeviceDetailView, DeviceListView
from main.views.device_credentials import DeviceCredentialsDetailView
from main.views.device_from_conf import DeviceFromConfListView
from main.views.device_profile import DeviceProfileDetailView, DeviceProfileListView
from main.views.general_settings import GeneralSettingsDetailView
from main.views.guest import GuestCheckoutView, GuestDetailView, GuestListView
from main.views.guest_move_room import GuestMoveRoomListView
from main.views.integration_settings import IntegrationSettingsDetailView
from main.views.public_space import PublicSpaceDetailView, PublicSpaceListView
from main.views.room import RoomDetailView, RoomListView
from main.views.room_from_conf import RoomFromConfListView
from main.views.room_status import RoomHistoryStatusView
from main.views.room_type import RoomTypeDetailView, RoomTypeListView
from main.views.tenant import TenantListView
from main.views.webrtc import WebrtcAgentStatus, WebrtcBroker
from main.views.widget_type import WidgetTypeDetailView, WidgetTypeListView

urlpatterns = [
    path("general-settings/", GeneralSettingsDetailView.as_view(), name="general-settings-detail"),
    path("integration-settings/", IntegrationSettingsDetailView.as_view(), name="integration-settings-detail"),
    path("alarm-settings/", AlarmSettingsDetailView.as_view(), name="alarm-settings"),
    path("admin-settings/<str:key>/", AdminSettingsView.as_view(), name="admin-settings"),
    path("room/", RoomListView.as_view(), name="room-list"),
    path("room/<uuid:pk>/", RoomDetailView.as_view(), name="room-detail"),
    path("room-type/", RoomTypeListView.as_view(), name="room-type-list"),
    path("room-type/<uuid:pk>/", RoomTypeDetailView.as_view(), name="room-type-detail"),
    path("widget-type/", WidgetTypeListView.as_view(), name="widget-type-list"),
    path("widget-type/<uuid:pk>/", WidgetTypeDetailView.as_view(), name="widget-type-detail"),
    path("dashboard/", DashboardListView.as_view(), name="dashboard-list"),
    path("dashboard/<uuid:pk>/", DashboardDetailView.as_view(), name="dashboard-detail"),
    path("dashboard/type/", DashboardTypeView.as_view(), name="dashboard-type"),
    path("device/", DeviceListView.as_view(), name="device-list"),
    path("device/<uuid:pk>/", DeviceDetailView.as_view(), name="device-detail"),
    path("device-profile/", DeviceProfileListView.as_view(), name="device-profile-list"),
    path("device-profile/<uuid:pk>/", DeviceProfileDetailView.as_view(), name="device-profile-detail"),
    path("device/<str:token>/credentials/", DeviceCredentialsDetailView.as_view(), name="device-credentials-detail"),
    path("guest/", GuestListView.as_view(), name="guest-list"),
    path("guest/<uuid:pk>/", GuestDetailView.as_view(), name="guest-detail"),
    path("guest/move/room/", GuestMoveRoomListView.as_view(), name="guest-move-room-list"),
    path("checkout/", GuestCheckoutView.as_view(), name="guest-checkout-detail"),
    path("room-status/", RoomHistoryStatusView.as_view(), name="room-status-list"),
    path("blocks-floors/", BlockFloorsView.as_view(), name="block-floors-list"),
    path("devices-from-configuration/", DeviceFromConfListView.as_view(), name="device-from-conf-list"),
    path("rooms-from-configuration/", RoomFromConfListView.as_view(), name="room-from-conf-list"),
    # Public space
    path("public-space/", PublicSpaceListView.as_view(), name="public-space-list"),
    path("public-space/<uuid:pk>/", PublicSpaceDetailView.as_view(), name="public-space-detail"),
    # For SuperUser
    path("tenant/", TenantListView.as_view(), name="tenant-list"),
    path("connector-url/", WebrtcBroker.as_view(), name="webrtc-open"),
    path("webrtc-connector-status/", WebrtcAgentStatus.as_view(), name="webrtc-gateways-status"),
]
