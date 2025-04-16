from django.urls import path
from services.views.integration import IntegrationListView, IntegrationDetailView

urlpatterns = [
    path("integrations/", IntegrationListView.as_view(), name="integration-list"),
    path("integration/<uuid:pk>/", IntegrationDetailView.as_view(), name="integration-detail"),
]
