import uuid
from unittest.mock import patch, call
from django.urls import reverse

from core.tests.base import BaseTestCase
from access_manager.models import (
    Group, GroupRoom, GroupPublicSpace
)


class GroupViewTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
        "room.yaml",
        "guest.yaml",
        "public_space.yaml",
        "customer.yaml",
        "device_profile.yaml",
        "device.yaml",
        "group.yaml",
        "group_public_space.yaml",
        "group_room.yaml",
        "staff.yaml",
        "card.yaml",
        "card_slot.yaml",
        "guest_public_space.yaml",
        "guest_card.yaml",
        "staff_card.yaml",
        "need_sync_device.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.karina_token)
        self.list_url = reverse("access_manager:group-list")
        self.detail_url_template = "access_manager:group-detail"

    # GroupListView Tests
    def test_list_groups_basic(self):
        """Test basic listing of groups"""
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertGreater(len(response.data["results"]), 0)

    def test_list_groups_with_search(self):
        """Test listing groups with search"""
        response = self.client.get(self.list_url, {
            "search_field": "name",
            "search_value": "Housekeeping"
        })

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data["count"], 0)

    def test_list_groups_with_sorting(self):
        """Test listing groups with sorting"""
        response = self.client.get(self.list_url, {
            "sort_by": ["-name"]
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        response = self.client.get(self.list_url, {
            "sort_by": ["name"]
        })
        self.assertEqual(response.status_code, 200)

    def test_list_groups_with_pagination(self):
        """Test listing groups with pagination"""
        response = self.client.get(self.list_url, {
            "page": 1,
            "size": 1
        })

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data["results"]), 1)

    @patch('access_manager.tasks.room_card.manage_cards_for_room_task.delay')
    @patch('access_manager.tasks.public_space_card.manage_cards_for_public_space_task.delay')
    def test_create_group_success(self, mock_public_space_task, mock_room_task):
        """Test successful group creation"""
        mock_room_task.return_value = None
        mock_public_space_task.return_value = None

        payload = {
            "name": "Test Group",
            "group_type": "HOUSEKEEPING",
            "week_days": ["monday", "tuesday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "rooms_ids": ["df77f910-2dcd-45cf-b6be-054c744561a7"],  # Room 101
            "public_spaces_ids": ["ad09aa20-77b8-457a-bfc4-5dee69790243"]  # Lobby
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Test Group")
        self.assertEqual(response.data["group_type"], "HOUSEKEEPING")

        group_id = response.data["id"]
        self.assertTrue(
            GroupRoom.objects.filter(
                group_id=group_id,
                room_id="df77f910-2dcd-45cf-b6be-054c744561a7"
            ).exists()
        )

        self.assertTrue(
            GroupPublicSpace.objects.filter(
                group_id=group_id,
                public_space_id="ad09aa20-77b8-457a-bfc4-5dee69790243"
            ).exists()
        )

        mock_room_task.assert_called_once_with(
            group_id, "df77f910-2dcd-45cf-b6be-054c744561a7", "connect", card_num=None
        )
        mock_public_space_task.assert_called_once_with(
            group_id, "ad09aa20-77b8-457a-bfc4-5dee69790243", "connect", card_num=None
        )

    def test_create_group_validation_error(self):
        """Test group creation with validation errors"""
        payload = {
            "name": "",  # Invalid empty name
            "group_type": "Hello world",  # Invalid group type
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)

    def test_create_group_missing_required_fields(self):
        """Test group creation with missing required fields"""
        payload = {
            "group_type": "MASTER_CARD",
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, 400)

    @patch('access_manager.tasks.room_card.manage_cards_for_room_task.delay')
    @patch('access_manager.tasks.public_space_card.manage_cards_for_public_space_task.delay')
    def test_create_group_without_rooms_and_spaces(self, mock_public_space_task, mock_room_task):
        """Test creating group without rooms and public spaces"""
        mock_room_task.return_value = None
        mock_public_space_task.return_value = None

        payload = {
            "name": "Minimal Group",
            "group_type": "HOUSEKEEPING",
            "week_days": ["monday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "rooms_ids": [],
            "public_spaces_ids": []
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Minimal Group")

        # Verify no task functions were called since no rooms/spaces
        mock_room_task.assert_not_called()
        mock_public_space_task.assert_not_called()

    # GroupDetailView Tests
    def test_get_group_detail_success(self):
        """Test successful retrieval of group details"""
        group_id = "ee74097b-fb0a-4e7b-9cdc-10dc54eab55c"  # Housekeeping Group
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], group_id)
        self.assertEqual(response.data["name"], "Housekeeping Group")
        self.assertIn("count_staff", response.data)

    def test_get_group_detail_not_found(self):
        """Test group detail with non-existent ID"""
        url = reverse(self.detail_url_template, kwargs={"pk": str(uuid.uuid4())})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_get_group_detail_inactive_group(self):
        """Test getting details of inactive group"""
        # Make Housekeeping Group inactive
        group = Group.objects.get(id="ee74097b-fb0a-4e7b-9cdc-10dc54eab55c")
        group.is_active = False
        group.save()

        url = reverse(self.detail_url_template, kwargs={"pk": group.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    @patch('access_manager.tasks.room_card.manage_cards_for_room_task.delay')
    @patch('access_manager.tasks.public_space_card.manage_cards_for_public_space_task.delay')
    def test_update_group_success(self, mock_public_space_task, mock_room_task):
        """Test successful group update"""
        mock_room_task.return_value = None
        mock_public_space_task.return_value = None

        group_id = "ee74097b-fb0a-4e7b-9cdc-10dc54eab55c"  # Housekeeping Group
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})

        payload = {
            "name": "Updated Housekeeping Group",
            "group_type": "MASTER_CARD",
            "week_days": ["monday", "tuesday", "wednesday"],
            "start_time": "08:30",
            "end_time": "17:30",
            "rooms_ids": ["ab09aa20-77b8-457a-bfc4-5dee69790241"],  # Room 102
            "public_spaces_ids": ["ad09aa20-77b8-457a-bfc4-5dee69790242"]  # Conference Room
        }

        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Housekeeping Group")
        self.assertEqual(response.data["start_time"], "08:30")

    @patch('access_manager.tasks.room_card.manage_cards_for_room_task.delay')
    @patch('access_manager.tasks.public_space_card.manage_cards_for_public_space_task.delay')
    def test_update_group_rooms_addition_removal(self, mock_public_space_task, mock_room_task):
        """Test updating group with room additions and removals - verify only changed rooms trigger tasks"""
        mock_room_task.return_value = None
        mock_public_space_task.return_value = None

        group_id = "eb3452a8-de98-4a2b-84c9-61d103669830"  # Engineering Group
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})

        # Engineering Group currently has Room 101 (df77f910-2dcd-45cf-b6be-054c744561a7)
        # We're updating to have Room 102 and Room 103
        payload = {
            "name": "Engineering Group",
            "group_type": "MASTER_CARD",
            "week_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "rooms_ids": [
                "ab09aa20-77b8-457a-bfc4-5dee69790241",  # Room 102 (new)
                "cb09aa20-77b8-457a-bfc5-5dee69790243"  # Room 103 (new)
            ],
            "public_spaces_ids": []
        }

        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, 200)

        # Verify disconnect task was called for removed room (Room 101)
        expected_calls = [
            call(group_id, "df77f910-2dcd-45cf-b6be-054c744561a7", "disconnect", card_num=None),  # Remove Room 101
            call(group_id, "ab09aa20-77b8-457a-bfc4-5dee69790241", "connect", card_num=None),  # Add Room 102
            call(group_id, "cb09aa20-77b8-457a-bfc5-5dee69790243", "connect", card_num=None),  # Add Room 103
        ]
        mock_room_task.assert_has_calls(expected_calls, any_order=False)

    @patch('access_manager.tasks.room_card.manage_cards_for_room_task.delay')
    @patch('access_manager.tasks.public_space_card.manage_cards_for_public_space_task.delay')
    def test_update_group_public_spaces_addition_removal(self, mock_public_space_task, mock_room_task):
        """Test updating group with public space additions and removals - verify only changed spaces trigger tasks"""
        mock_room_task.return_value = None
        mock_public_space_task.return_value = None

        group_id = "ee74097b-fb0a-4e7b-9cdc-10dc54eab55c"  # Housekeeping Group
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})
        payload = {
            "name": "Housekeeping Group",
            "group_type": "HOUSEKEEPING",
            "week_days": ["all_days"],
            "start_time": "08:00",
            "end_time": "18:00",
            "rooms_ids": [],
            "public_spaces_ids": ["ad09aa20-77b8-457a-bfc4-5dee69790242"]  # Conference Room only
        }

        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, 200)

        expected_calls = [
            call(group_id, "ad09aa20-77b8-457a-bfc4-5dee69790243", "disconnect", card_num=None),  # Remove Lobby
            call(group_id, "ad09aa20-77b8-457a-bfc4-5dee69790242", "connect", card_num=None),  # Keep Conference Room
        ]
        mock_public_space_task.assert_has_calls(expected_calls, any_order=False)

    def test_update_group_not_found(self):
        """Test updating non-existent group"""
        url = reverse(self.detail_url_template, kwargs={"pk": str(uuid.uuid4())})

        payload = {
            "name": "Non-existent Group",
            "group_type": "HOUSEKEEPING",
        }

        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, 404)

    def test_update_group_validation_error(self):
        """Test updating group with validation errors"""
        group_id = "ee74097b-fb0a-4e7b-9cdc-10dc54eab55c"
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})

        payload = {
            "name": "",  # Invalid empty name
            "group_type": "Hello world"  # Invalid group type
        }

        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_delete_group_success(self):
        """Test successful group deletion (soft delete)"""
        group_id = "ee74097b-fb0a-4e7b-9cdc-10dc54eab55c"
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)

        # Verify group is soft deleted
        group = Group.objects.get(id=group_id)
        self.assertFalse(group.is_active)

        # Verify GroupRoom relationships are deleted
        self.assertFalse(
            GroupRoom.objects.filter(group_id=group_id).exists()
        )

    def test_delete_group_not_found(self):
        """Test deleting non-existent group"""
        url = reverse(self.detail_url_template, kwargs={"pk": str(uuid.uuid4())})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)

    def test_delete_inactive_group(self):
        """Test deleting already inactive group"""
        group = Group.objects.get(id="ee74097b-fb0a-4e7b-9cdc-10dc54eab55c")
        group.is_active = False
        group.save()

        url = reverse(self.detail_url_template, kwargs={"pk": group.id})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 404)

    # Filter and Search Tests
    def test_list_groups_invalid_search_field(self):
        """Test listing groups with invalid search field"""
        response = self.client.get(self.list_url, {
            "search_field": "invalid_field",
            "search_value": "test"
        })

        self.assertEqual(response.status_code, 400)

    def test_list_groups_invalid_sort_field(self):
        """Test listing groups with invalid sort field"""
        response = self.client.get(self.list_url, {
            "sort_by": ["invalid_field"]
        })

        self.assertEqual(response.status_code, 400)

    def test_list_groups_pagination_edge_cases(self):
        """Test pagination with edge cases"""
        # Test with page 0
        response = self.client.get(self.list_url, {
            "page": 0,
            "size": 10
        })

        self.assertEqual(response.status_code, 200)

        # Test with very large page number
        response = self.client.get(self.list_url, {
            "page": 999,
            "size": 10
        })

        self.assertEqual(response.status_code, 200)

    @patch('access_manager.tasks.room_card.manage_cards_for_room_task.delay')
    def test_create_group_task_exception_handling(self, mock_room_task):
        """Test group creation when task raises exception"""
        mock_room_task.side_effect = Exception("Task failed")

        payload = {
            "name": "Test Group with Task Error",
            "group_type": "HOUSEKEEPING",
            "week_days": ["monday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "rooms_ids": ["df77f910-2dcd-45cf-b6be-054c744561a7"],
            "public_spaces_ids": []
        }

        # The view should still succeed even if tasks fail
        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Test Group with Task Error")

    def test_create_group_invalid_room_id(self):
        """Test group creation with invalid room ID"""
        payload = {
            "name": "Test Group",
            "group_type": "HOUSEKEEPING",
            "week_days": ["monday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "rooms_ids": [str(uuid.uuid4())],  # Non-existent room
            "public_spaces_ids": []
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_create_group_invalid_public_space_id(self):
        """Test group creation with invalid public space ID"""
        payload = {
            "name": "Test Group",
            "group_type": "HOUSEKEEPING",
            "week_days": ["monday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "rooms_ids": [],
            "public_spaces_ids": [str(uuid.uuid4())]  # Non-existent public space
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_serializer_to_representation_with_staff_count(self):
        """Test that serializer properly adds count_staff to representation"""
        group_id = "ee74097b-fb0a-4e7b-9cdc-10dc54eab55c"  # Group with staff
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("count_staff", response.data)
        self.assertIsInstance(response.data["count_staff"], int)

    @patch('access_manager.tasks.room_card.manage_cards_for_room_task.delay')
    @patch('access_manager.tasks.public_space_card.manage_cards_for_public_space_task.delay')
    def test_update_group_empty_rooms_and_spaces(self, mock_public_space_task, mock_room_task):
        """Test updating group to remove all rooms and public spaces"""
        mock_room_task.return_value = None
        mock_public_space_task.return_value = None

        group_id = "ee74097b-fb0a-4e7b-9cdc-10dc54eab55c"
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})

        payload = {
            "name": "Updated Group",
            "group_type": "ENGINEERING",
            "week_days": ["monday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "rooms_ids": [],
            "public_spaces_ids": []
        }

        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, 200)

        # Verify disconnect tasks were called for existing relationships
        # Housekeeping Group has 2 public spaces: Lobby and Conference Room
        expected_public_space_calls = [
            call(group_id, "ad09aa20-77b8-457a-bfc4-5dee69790243", "disconnect", card_num=None),  # Lobby
            call(group_id, "ad09aa20-77b8-457a-bfc4-5dee69790242", "disconnect", card_num=None),  # Conference Room
        ]
        mock_public_space_task.assert_has_calls(expected_public_space_calls, any_order=True)

    @patch('access_manager.tasks.room_card.manage_cards_for_room_task.delay')
    @patch('access_manager.tasks.public_space_card.manage_cards_for_public_space_task.delay')
    def test_update_group_with_same_relationships(self, mock_public_space_task, mock_room_task):
        """Test updating group with same room and public space relationships - should still call connect"""
        mock_room_task.return_value = None
        mock_public_space_task.return_value = None

        group_id = "eb3452a8-de98-4a2b-84c9-61d103669830"  # Engineering Group
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})

        payload = {
            "name": "Engineering Group Updated",
            "group_type": "MASTER_CARD",
            "week_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "rooms_ids": ["df77f910-2dcd-45cf-b6be-054c744561a7"],  # Same as existing
            "public_spaces_ids": []
        }

        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Engineering Group Updated")

        # Since we're keeping the same room, it should call connect for the existing room
        mock_room_task.assert_called_once_with(
            group_id, "df77f910-2dcd-45cf-b6be-054c744561a7", "connect", card_num=None
        )

    @patch('access_manager.tasks.room_card.manage_cards_for_room_task.delay')
    @patch('access_manager.tasks.public_space_card.manage_cards_for_public_space_task.delay')
    def test_update_group_partial_room_changes(self, mock_public_space_task, mock_room_task):
        """Test complex room update scenario: keep some, remove some, add new"""
        mock_room_task.return_value = None
        mock_public_space_task.return_value = None

        # First, let's add multiple rooms to Engineering Group to test complex scenario
        group = Group.objects.get(id="eb3452a8-de98-4a2b-84c9-61d103669830")

        # Add Room 102 to the group manually for testing
        GroupRoom.objects.create(
            group=group,
            room_id="ab09aa20-77b8-457a-bfc4-5dee69790241"  # Room 102
        )

        group_id = str(group.id)
        url = reverse(self.detail_url_template, kwargs={"pk": group_id})

        # Now Engineering Group has Room 101 and Room 102
        # Update to have Room 101 and Room 103 (remove 102, add 103, keep 101)
        payload = {
            "name": "Engineering Group",
            "group_type": "MASTER_CARD",
            "week_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "rooms_ids": [
                "df77f910-2dcd-45cf-b6be-054c744561a7",  # Room 101 (keep)
                "cb09aa20-77b8-457a-bfc5-5dee69790243"  # Room 103 (add)
            ],
            "public_spaces_ids": []
        }

        response = self.client.put(url, payload, format="json")

        self.assertEqual(response.status_code, 200)

        # Verify the correct sequence of calls
        expected_calls = [
            call(group_id, "ab09aa20-77b8-457a-bfc4-5dee69790241", "disconnect", card_num=None),  # Remove Room 102
            call(group_id, "df77f910-2dcd-45cf-b6be-054c744561a7", "connect", card_num=None),  # Keep Room 101
            call(group_id, "cb09aa20-77b8-457a-bfc5-5dee69790243", "connect", card_num=None),  # Add Room 103
        ]
        mock_room_task.assert_has_calls(expected_calls, any_order=False)