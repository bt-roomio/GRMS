from card.views.group import GroupDetailView, GroupListView
from django.urls import path

urlpatterns = [
    path("groups/", GroupListView.as_view(), name="group-list"),
    path("group/<uuid:pk>/", GroupDetailView.as_view(), name="group-detail"),
]
