from django.urls import path

from shuttle.views.attributes import AttributeListView
from shuttle.views.controller_file import ControllerFileListView
from shuttle.views.json_rpc import JsonRpcView
from shuttle.views.relation import RelationListView, RelationDetailView

urlpatterns = [
    path("attributes/<uuid:deviceId>/<str:scope>/", AttributeListView.as_view(), name="attributes-list"),
    path("relation/", RelationListView.as_view(), name="relation-list"),
    path("relation/<uuid:pk>/", RelationDetailView.as_view(), name="relation-detail"),
    path("rpc/<uuid:device_id>/", JsonRpcView.as_view(), name="json-rpc-view"),
    path("controller/file/", ControllerFileListView.as_view(), name="controller-file-view"),
]
