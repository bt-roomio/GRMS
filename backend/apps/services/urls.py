from django.urls import path

from services.views.integration import IntegrationDetailView, IntegrationListView
from services.views.sber_get_room import SberGetRoomDetailView

urlpatterns = [
    path("integrations/", IntegrationListView.as_view(), name="integration-list"),
    path("integration/<uuid:pk>/", IntegrationDetailView.as_view(), name="integration-detail"),
    path("sber/", SberGetRoomDetailView.as_view(), name="sber-get-room-detail"),
]
