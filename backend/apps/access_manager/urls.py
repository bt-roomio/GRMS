from access_manager.views.card import CardDetailView, CardListView
from access_manager.views.group import GroupDetailView, GroupListView
from access_manager.views.staff import StaffDetailView, StaffListView
from django.urls import path

urlpatterns = [
    # Group
    path("groups/", GroupListView.as_view(), name="group-list"),
    path("group/<uuid:pk>/", GroupDetailView.as_view(), name="group-detail"),
    # Staff
    path("staff/", StaffListView.as_view(), name="staff-list"),
    path("staff/<uuid:pk>/", StaffDetailView.as_view(), name="staff-detail"),
    # Public space
    path("card/", CardListView.as_view(), name="card-list"),
    path("card/<uuid:pk>/", CardDetailView.as_view(), name="card-detail"),
]
