from django.urls import path

from access_manager.views.card import CardDetailView, CardListView, DisconnectCardView
from access_manager.views.card_logs_export import ExportCardLogsExcelView
from access_manager.views.group import GroupDetailView, GroupListView
from access_manager.views.guest_card import GuestCardView
from access_manager.views.housekeeping_room import HousekeepingRoomView
from access_manager.views.staff import StaffDetailView, StaffListView
from access_manager.views.staff_card import StaffCardView
from access_manager.views.sync_device import SyncDeviceByDeviceDetailView, SyncDeviceDetailView, SyncDeviceView

urlpatterns = [
    path("groups/", GroupListView.as_view(), name="group-list"),
    path("group/<uuid:pk>/", GroupDetailView.as_view(), name="group-detail"),
    path("housekeeping-room/", HousekeepingRoomView.as_view(), name="housekeeping-room"),
    path("staff/", StaffListView.as_view(), name="staff-list"),
    path("staff/<uuid:pk>/", StaffDetailView.as_view(), name="staff-detail"),
    path("card/", CardListView.as_view(), name="card-list"),
    path("card/<uuid:pk>/", CardDetailView.as_view(), name="card-detail"),
    path("card-logs/export/", ExportCardLogsExcelView.as_view(), name="export-card-logs-excel"),
    path("guest-card/", GuestCardView.as_view(), name="guest-card"),
    path("staff-card/", StaffCardView.as_view(), name="staff-card"),
    path("disconnect-card/", DisconnectCardView.as_view(), name="disconnect-card"),
    path("sync/", SyncDeviceView.as_view(), name="need-sync"),
    path("sync/<uuid:pk>/", SyncDeviceDetailView.as_view(), name="need-sync-detail"),
    path("sync-by-device/<uuid:device_id>/", SyncDeviceByDeviceDetailView.as_view(), name="need-sync-by-device-detail"),
]
