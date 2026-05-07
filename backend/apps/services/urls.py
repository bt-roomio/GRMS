from django.urls import path

from services.views.integration import IntegrationDetailView, IntegrationListView
from services.views.lockkeys import LockKeyDoorOpenView, LockKeyDoorsListView
from services.views.mews_integration import MewsIntegrationView
from services.views.sber_get_room import SberGetRoomDetailView
from services.views.sber_window import SberWindowView

urlpatterns = [
    path("integrations/", IntegrationListView.as_view(), name="integration-list"),
    path("integration/<uuid:pk>/", IntegrationDetailView.as_view(), name="integration-detail"),
    path("sber/", SberGetRoomDetailView.as_view(), name="sber-get-room-detail"),
    path("sber-window/", SberWindowView.as_view(), name="sber-window-detail"),
    path("mews-integration/", MewsIntegrationView.as_view(), name="mews-integration"),
    path("lockkeys/doors/", LockKeyDoorsListView.as_view(), name="lockkeys-doors-list"),
    path("lockkeys/doors/<str:space_id>/open/", LockKeyDoorOpenView.as_view(), name="lockkeys-door-open"),
]
