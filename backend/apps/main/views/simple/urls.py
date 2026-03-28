from django.urls import path

from main.views.simple.dashboard import DashboardQuickListView
from main.views.simple.device import DeviceQuickListView
from main.views.simple.device_profile import DeviceProfileQuickListView
from main.views.simple.group import GroupQuickListView
from main.views.simple.guest import GuestQuickListView
from main.views.simple.public_space import PublicSpaceQuickListView
from main.views.simple.role import RoleQuickListView
from main.views.simple.room import RoomQuickListView
from main.views.simple.room_type import RoomTypeQuickListView
from main.views.simple.staff import StaffQuickListView

urlpatterns = [
    path("device/", DeviceQuickListView.as_view(), name="simple-device-list"),
    path("device-profile/", DeviceProfileQuickListView.as_view(), name="simple-device-profile-list"),
    path("room/", RoomQuickListView.as_view(), name="simple-room-list"),
    path("room-type/", RoomTypeQuickListView.as_view(), name="simple-room-type-list"),
    path("dashboard/", DashboardQuickListView.as_view(), name="simple-dashboard-list"),
    path("public-space/", PublicSpaceQuickListView.as_view(), name="simple-public-space-list"),
    path("guest/", GuestQuickListView.as_view(), name="simple-guest-list"),
    path("staff/", StaffQuickListView.as_view(), name="simple-staff-list"),
    path("role/", RoleQuickListView.as_view(), name="simple-role-list"),
    path("group/", GroupQuickListView.as_view(), name="simple-group-list"),
]
