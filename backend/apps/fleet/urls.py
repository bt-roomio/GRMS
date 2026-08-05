from django.urls import path

from fleet.views.audit_log import FleetNodeAuditLogView
from fleet.views.command import FleetNodeRunCommandView
from fleet.views.enrollment import FleetNodeInstallView
from fleet.views.fleet_node import (
    FleetNodeDetailView,
    FleetNodeListView,
    FleetNodeStatusView,
)
from fleet.views.upload import FleetNodeUploadView

urlpatterns = [
    path("nodes/", FleetNodeListView.as_view(), name="node-list"),
    path("nodes/<uuid:pk>/", FleetNodeDetailView.as_view(), name="node-detail"),
    path("nodes/<uuid:pk>/install/", FleetNodeInstallView.as_view(), name="node-install"),
    path("nodes/<uuid:pk>/run/", FleetNodeRunCommandView.as_view(), name="node-run"),
    path("nodes/<uuid:pk>/upload/", FleetNodeUploadView.as_view(), name="node-upload"),
    path("nodes/<uuid:pk>/refresh/", FleetNodeStatusView.as_view(), name="node-refresh"),
    path(
        "nodes/<uuid:pk>/audit-logs/",
        FleetNodeAuditLogView.as_view(),
        name="node-audit-logs",
    ),
]
