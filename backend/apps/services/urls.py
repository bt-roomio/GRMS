from django.urls import path

from services.views.integration import IntegrationDetailView, IntegrationListView
from services.views.lockkeys import LockKeyDoorOpenView, LockKeyDoorsListView
from services.views.mews_integration import MewsIntegrationView
from services.views.room import RoomListView
from services.views.sber_get_room import SberGetRoomDetailView
from services.views.sber_window import SberWindowView
from services.views.tags import TagDetailView, TagsByRoomListView

urlpatterns = [
    path("integrations/", IntegrationListView.as_view(), name="integration-list"),
    path("integration/<uuid:pk>/", IntegrationDetailView.as_view(), name="integration-detail"),
    path("sber/", SberGetRoomDetailView.as_view(), name="sber-get-room-detail"),
    path("sber-window/", SberWindowView.as_view(), name="sber-window-detail"),
    path("mews-integration/", MewsIntegrationView.as_view(), name="mews-integration"),
    path("lockkeys/doors/", LockKeyDoorsListView.as_view(), name="lockkeys-doors-list"),
    path("lockkeys/doors/<str:space_id>/open/", LockKeyDoorOpenView.as_view(), name="lockkeys-door-open"),
    path("rooms/", RoomListView.as_view(), name="room-list"),
    path("tags/<uuid:room_id>/", TagsByRoomListView.as_view(), name="tags-by-room-list"),
    path("tag/<uuid:tag_id>/", TagDetailView.as_view(), name="tag-detail"),
]
