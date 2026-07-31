from django.urls import path

from fleet.views.fleet_node import (
    FleetNodeAuditLogView,
    FleetNodeDetailView,
    FleetNodeInstallView,
    FleetNodeListView,
    FleetNodeRunCommandView,
    FleetNodeStatusView,
)

urlpatterns = [
    path("nodes/", FleetNodeListView.as_view(), name="node-list"),
    path("nodes/<uuid:pk>/", FleetNodeDetailView.as_view(), name="node-detail"),
    path("nodes/<uuid:pk>/install/", FleetNodeInstallView.as_view(), name="node-install"),
    path("nodes/<uuid:pk>/run/", FleetNodeRunCommandView.as_view(), name="node-run"),
    path("nodes/<uuid:pk>/refresh/", FleetNodeStatusView.as_view(), name="node-refresh"),
    path(
        "nodes/<uuid:pk>/audit-logs/",
        FleetNodeAuditLogView.as_view(),
        name="node-audit-logs",
    ),
]
