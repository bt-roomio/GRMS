from access_manager.views.group import GroupDetailView, GroupListView
from access_manager.views.public_space import PublicSpaceDetailView, PublicSpaceListView
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
    path("public-space/", PublicSpaceListView.as_view(), name="public-space-list"),
    path("public-space/<uuid:pk>/", PublicSpaceDetailView.as_view(), name="public-space-detail"),
]
