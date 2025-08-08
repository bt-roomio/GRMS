from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Guest


class GuestMoveRoomViewTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "guest.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.from_room_id = "df77f910-2dcd-45cf-b6be-054c744561a7"
        self.to_room_id = "ab09aa20-77b8-457a-bfc4-5dee69790241"
        self.empty_room_id = "cb09aa20-77b8-457a-bfc5-5dee69790243"
        self.url = reverse("main:guest-move-room-list")

    def test_guest_move_room_not_found(self):
        response = self.client.generic(
            method="PUT",
            path=f"{self.url}?from_room={self.empty_room_id}&to_room={self.to_room_id}",
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "`from_room` guests doesn't exist!")

    def test_guest_move_room_success(self):
        guest = Guest.objects.get(pk="5b66af57-fb27-4c26-9986-b9994e644605")
        self.assertEqual(str(guest.room_id), self.from_room_id)

        response = self.client.generic(
            method="PUT",
            path=f"{self.url}?from_room={self.from_room_id}&to_room={self.to_room_id}",
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], "Guests moved successfully!")

        guest.refresh_from_db()
        self.assertEqual(str(guest.room_id), self.to_room_id)
