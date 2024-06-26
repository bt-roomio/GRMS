from django.urls import path

from shuttle.views.attributes import AttributeListView


urlpatterns = [
    path("attributes/<uuid:deviceId>/<str:scope>/", AttributeListView.as_view(), name="attributes-list"),
]
