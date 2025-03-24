from django.urls import path
from services.views.integration import InegrationDetailView, InegrationListView

urlpatterns = [
    path("integrations/", InegrationListView.as_view(), name="integration-list"),
    path("integration/<uuid:pk>/", InegrationDetailView.as_view(), name="integration-detail"),
]
