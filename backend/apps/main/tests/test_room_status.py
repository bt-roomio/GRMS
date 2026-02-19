from unittest.mock import patch

from django.urls import reverse

from core.tests.base import BaseTestCase


class RoomHistoryStatusTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.url = reverse("main:room-status-list")

    # ── helpers ──────────────────────────────────────────────────────────
    def _mock_statuses(self, data):
        """Patch Room.objects.statuses to return controlled data."""
        return patch(
            "main.views.room_status.Room.objects.statuses",
            return_value=data,
        )

    # ── success cases ────────────────────────────────────────────────────
    def test_get_returns_200_with_valid_data(self):
        """GET returns 200 when statuses queryset returns valid data."""
        mock_data = [
            {"status": "Available", "last_24_hour": 3, "diff_previous_day": 0},
            {"status": "CheckedIn", "last_24_hour": 1, "diff_previous_day": 1},
        ]
        with self._mock_statuses(mock_data):
            response = self.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 2)

    def test_get_response_fields(self):
        """Each item in the response contains status, last_24_hour, diff_previous_day."""
        mock_data = [
            {"status": "Available", "last_24_hour": 5, "diff_previous_day": 2},
        ]
        with self._mock_statuses(mock_data):
            response = self.get(self.url)

        self.assertEqual(response.status_code, 200)
        item = response.data[0]
        self.assertEqual(item["status"], "Available")
        self.assertEqual(item["last_24_hour"], 5)
        self.assertEqual(item["diff_previous_day"], 2)

    def test_get_empty_statuses(self):
        """GET returns 200 with empty list when no rooms match."""
        with self._mock_statuses([]):
            response = self.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_get_multiple_statuses(self):
        """GET correctly handles multiple status groups."""
        mock_data = [
            {"status": "Available", "last_24_hour": 10, "diff_previous_day": -2},
            {"status": "CheckedIn", "last_24_hour": 3, "diff_previous_day": 1},
            {"status": "Occupied", "last_24_hour": 2, "diff_previous_day": 0},
            {"status": "Reserved", "last_24_hour": 1, "diff_previous_day": 1},
            {"status": "MakeUpRoom", "last_24_hour": 0, "diff_previous_day": 0},
        ]
        with self._mock_statuses(mock_data):
            response = self.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 5)
        statuses = [item["status"] for item in response.data]
        self.assertIn("Available", statuses)
        self.assertIn("Occupied", statuses)

    # ── serializer validation ────────────────────────────────────────────
    def test_get_invalid_data_returns_400(self):
        """GET returns 400 when queryset data fails serializer validation."""
        # Missing required fields triggers validation error
        mock_data = [{"status": "Available"}]
        with self._mock_statuses(mock_data):
            response = self.get(self.url)

        self.assertEqual(response.status_code, 400)

    # ── Permission / Auth ────────────────────────────────────────────────
    def test_get_unauthenticated_rejected(self):
        """Unauthenticated request is rejected."""
        self.client.credentials()
        response = self.get(self.url)
        self.assertIn(response.status_code, (401, 403))
