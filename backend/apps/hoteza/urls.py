from django.urls import path
from hoteza.views.checkin import CheckInListView
from hoteza.views.checkout import CheckOutListView
from hoteza.views.dnd import DNDListView
from hoteza.views.guest_change import GuestChangeListView

urlpatterns = [
    path("checkin", CheckInListView.as_view(), name="checkin-list-view"),
    path("checkout", CheckOutListView.as_view(), name="checkout-list-view"),
    path("guestchange", GuestChangeListView.as_view(), name="guest-change-view"),
    path("dnd", DNDListView.as_view(), name="dnd-view"),
]
