from django.urls import path

from shuttle.views.attributes import AttributeListView, AttributesChangeRPCView
from shuttle.views.controller_file import ControllerFileListView
from shuttle.views.json_rpc import JsonRPCView
from shuttle.views.latest_ts_kv import LatestTsKvListView
from shuttle.views.relation import RelationDetailView, RelationListView
from shuttle.views.remove_attribute import RemoveAttribute
from shuttle.views.temp_change import TempAPIChangeTsKvLatest
from shuttle.views.ts_kv import TsKvListView

urlpatterns = [
    path("attributes/<uuid:device_id>/<str:scope>/", AttributeListView.as_view(), name="attributes-list"),
    path("relation/", RelationListView.as_view(), name="relation-list"),
    path("relation/<uuid:pk>/", RelationDetailView.as_view(), name="relation-detail"),
    path("rpc/<uuid:device_id>/", JsonRPCView.as_view(), name="json-rpc-view"),
    path("controller/file/", ControllerFileListView.as_view(), name="controller-file-view"),
    path("telemetry/<uuid:device_id>/<str:scope>/", RemoveAttribute.as_view(), name="remove-attribute-view"),
    path("telemetry/<str:entity_type>/<uuid:entity_id>/", TsKvListView.as_view(), name="ts-kv-list-view"),
    path(
        "attributes-change/<str:entity_type>/<uuid:entity_id>/",
        AttributesChangeRPCView.as_view(),
        name="attributes-change-view",
    ),
    # Integration
    path("rpc/<uuid:tenant_id>/<int:room_number>/", JsonRPCView.as_view(), name="tenant-id-room-id-json-rpc-view"),
    path("rpc/<str:hotel_id>/<int:room_number>/", JsonRPCView.as_view(), name="hoteza-hotel-id-json-rpc-view"),
    path(
        "latest-telemetry/<uuid:tenant_id>/<int:room_number>/",
        LatestTsKvListView.as_view(),
        name="tenant-id-room-id-latest-ts-kv-list-view",
    ),
    path(
        "latest-telemetry/<str:hotel_id>/<int:room_number>/",
        LatestTsKvListView.as_view(),
        name="tenant-id-room-id-latest-ts-kv-list-view",
    ),
    # Temp API
    path(
        "temp-api/<uuid:entity_id>/",
        TempAPIChangeTsKvLatest.as_view(),
        name="temp-api-change-ts-kv-latest",
    ),
]
