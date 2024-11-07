from django.urls import path

from shuttle.views.attributes import AttributeListView, AttributesChangeRPCView
from shuttle.views.controller_file import ControllerFileListView
from shuttle.views.controllers_status import ControllersStatusView
from shuttle.views.json_rpc import JsonRPCView
from shuttle.views.relation import RelationListView, RelationDetailView
from shuttle.views.remove_attribute import RemoveAttribute

urlpatterns = [
    path("attributes/<uuid:device_id>/<str:scope>/", AttributeListView.as_view(), name="attributes-list"),
    path("relation/", RelationListView.as_view(), name="relation-list"),
    path("relation/<uuid:pk>/", RelationDetailView.as_view(), name="relation-detail"),
    path("rpc/<uuid:device_id>/", JsonRPCView.as_view(), name="json-rpc-view"),
    path("controller/file/", ControllerFileListView.as_view(), name="controller-file-view"),
    path("telemetry/<uuid:device_id>/<str:scope>/", RemoveAttribute.as_view(), name="remove-attribute-view"),
    path(
        "attributes-change/<str:entity_type>/<uuid:entity_id>/",
        AttributesChangeRPCView.as_view(),
        name="attributes-change-view",
    ),
    path("controllers-status/", ControllersStatusView.as_view(), name="controllers-status"),
]
