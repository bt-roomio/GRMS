from django.urls import path

from services.views.integration import IntegrationDetailView, IntegrationListView

urlpatterns = [
    path("integrations/", IntegrationListView.as_view(), name="integration-list"),
    path("integration/<uuid:pk>/", IntegrationDetailView.as_view(), name="integration-detail"),
]
