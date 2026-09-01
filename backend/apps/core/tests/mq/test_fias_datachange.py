from unittest.mock import patch

from django.test import TestCase

from core.management.mq.fias import handle_fias
from core.management.mq.fias.exceptions import LookupFailure
from core.management.mq.fias.handlers import datachange
from main.models import Guest, Room

ROOM_101 = "df77f910-2dcd-45cf-b6be-054c744561a7"
ROOM_102 = "ab09aa20-77b8-457a-bfc4-5dee69790241"
ROOM_103 = "cb09aa20-77b8-457a-bfc5-5dee69790243"
GUEST_IN_101 = "5b66af57-fb27-4c26-9986-b9994e644605"
GUEST_IN_102 = "52d8ba26-6fac-463b-a131-c16410e42ede"
TENANT = "28c81921-f78e-4864-87d2-cec674f19d1c"


def datachange_message(**overrides):
    message = {
        "command": "datachange",
        "language": "English / American",
        "roomName": "102",
        "guestName": "Ytest",
        "shareFlag": False,
        "guestTitle": None,
        "messageDate": 1787745391000,
        "checkInDate": 1787810400000,
        "checkOutDate": 1787983200000,
        "oldRoomName": "101",
        "operationId": "datachange|IKI.GR.546051536||9793230|101|260825|230532",
        "workstationId": "THEOVASQL",
        "guestFirstName": None,
        "guestGroupNumber": None,
        "reservationNumber": "4001",
    }
    message.update(overrides)
    return message


class FiasDatachangeTest(TestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "room.yaml", "guest.yaml")

    def setUp(self):
        self.device = {
            "id": "01b72123-dbba-4aaa-b827-d2a12eadda5a",
            "name": "FIAS Gateway",
            "tenant_id": TENANT,
            "device_profile_id": None,
        }
        patcher = patch("services.management.commands.pms_handler.publish_guest_changes")
        self.publish_guest_changes = patcher.start()
        self.addCleanup(patcher.stop)

        move = patch(
            "core.management.mq.fias.handlers.datachange.handle_guest_move",
            side_effect=datachange.handle_guest_move,
        )
        self.handle_guest_move = move.start()
        self.addCleanup(move.stop)

    def test_moves_guest_found_by_old_room(self):
        handle_fias(datachange_message(), self.device)

        guest = Guest.objects.get(pk=GUEST_IN_101)
        self.assertEqual(str(guest.room_id), ROOM_102)
        self.assertEqual(guest.name, "Ytest")
        self.assertEqual(guest.language, "English / American")
        self.assertEqual(guest.check_in, 1787810400)
        # checkOutDate is snapped to the tenant's auto checkout time (default 12:00 UTC)
        self.assertEqual(guest.check_out, 1788004800)
        self.assertEqual(guest.additional_info["pms_reg_num"], "4001")
        self.assertEqual(guest.additional_info["room_share"], "0")
        self.publish_guest_changes.assert_called_once()

    def test_moves_guest_found_by_reservation_number(self):
        Guest.objects.filter(pk=GUEST_IN_101).update(additional_info={"pms_reg_num": "4001"})

        handle_fias(datachange_message(oldRoomName=None), self.device)

        guest = Guest.objects.get(pk=GUEST_IN_101)
        self.assertEqual(str(guest.room_id), ROOM_102)

    def test_null_fields_do_not_overwrite_guest_data(self):
        handle_fias(datachange_message(guestFirstName=None, language=None), self.device)

        guest = Guest.objects.get(pk=GUEST_IN_101)
        self.assertEqual(guest.lastname, "Amigoyev")
        self.assertIsNone(guest.language)

    def test_unknown_target_room_raises(self):
        with self.assertRaises(LookupFailure):
            handle_fias(datachange_message(roomName="999"), self.device)

        guest = Guest.objects.get(pk=GUEST_IN_101)
        self.assertEqual(str(guest.room_id), ROOM_101)

    def test_no_active_guest_raises(self):
        Guest.objects.filter(pk=GUEST_IN_101).update(is_active=False)

        with self.assertRaises(LookupFailure):
            handle_fias(datachange_message(), self.device)

    def test_old_room_wins_over_a_stale_reservation_match(self):
        # A stale stay in another room carries the same recycled reservation number
        Guest.objects.filter(pk=GUEST_IN_102).update(additional_info={"pms_reg_num": "4001"})

        handle_fias(datachange_message(roomName="103"), self.device)

        moved = Guest.objects.get(pk=GUEST_IN_101)
        untouched = Guest.objects.get(pk=GUEST_IN_102)
        self.assertEqual(str(moved.room_id), ROOM_103)
        self.assertEqual(str(untouched.room_id), ROOM_102)
        self.assertEqual(untouched.name, "Alexandr")

    def test_moves_every_guest_of_a_shared_reservation(self):
        Guest.objects.filter(pk=GUEST_IN_102).update(room_id=ROOM_101)

        handle_fias(datachange_message(roomName="103", shareFlag=True), self.device)

        first = Guest.objects.get(pk=GUEST_IN_101)
        second = Guest.objects.get(pk=GUEST_IN_102)
        self.assertEqual(str(first.room_id), ROOM_103)
        self.assertEqual(str(second.room_id), ROOM_103)
        self.assertEqual(self.publish_guest_changes.call_count, 2)

        # The message carries one identity, so it must not be stamped onto the group
        self.assertEqual(first.name, "Amigo")
        self.assertEqual(second.name, "Alexandr")
        self.assertEqual(second.lastname, "Slaven")
        # Dates and reservation number do apply to everyone on the booking
        self.assertEqual(first.check_in, 1787810400)
        self.assertEqual(second.check_in, 1787810400)

    def test_room_states_are_recalculated_on_both_sides(self):
        handle_fias(datachange_message(roomName="103"), self.device)

        left_behind = Room.objects.get(pk=ROOM_101)
        moved_into = Room.objects.get(pk=ROOM_103)
        self.assertIn(Room.Available, left_behind.state)
        self.assertNotIn(Room.CheckedIn, left_behind.state)
        self.assertIn(Room.CheckedIn, moved_into.state)
        self.assertNotIn(Room.Available, moved_into.state)

    def test_other_reservation_in_the_room_is_not_dragged_along(self):
        Guest.objects.filter(pk=GUEST_IN_102).update(room_id=ROOM_101, additional_info={"pms_reg_num": "4002"})

        with self.assertRaises(LookupFailure):
            handle_fias(datachange_message(roomName="103"), self.device)

        self.assertEqual(str(Guest.objects.get(pk=GUEST_IN_102).room_id), ROOM_101)

    def test_stored_json_null_reservation_does_not_block_the_move(self):
        Guest.objects.filter(pk=GUEST_IN_101).update(additional_info={"pms_reg_num": None})

        handle_fias(datachange_message(roomName="103"), self.device)

        self.assertEqual(str(Guest.objects.get(pk=GUEST_IN_101).room_id), ROOM_103)

    def test_same_room_update_skips_the_move_path(self):
        Guest.objects.filter(pk=GUEST_IN_101).update(additional_info={"pms_reg_num": "4001"})

        handle_fias(datachange_message(roomName="101", oldRoomName=None), self.device)

        guest = Guest.objects.get(pk=GUEST_IN_101)
        self.assertEqual(str(guest.room_id), ROOM_101)
        self.assertEqual(guest.name, "Ytest")
        self.assertEqual(guest.additional_info["pms_reg_num"], "4001")
        # handle_guest_move() would save the room row twice for an unchanged room
        self.handle_guest_move.assert_not_called()

    def test_guest_title_is_applied(self):
        Guest.objects.filter(pk=GUEST_IN_101).update(additional_info={"pms_reg_num": "4001"})

        handle_fias(datachange_message(roomName="101", oldRoomName=None, guestTitle="Mr."), self.device)

        self.assertEqual(Guest.objects.get(pk=GUEST_IN_101).title, "Mr.")

    def test_title_is_applied_on_a_move_too(self):
        handle_fias(datachange_message(guestTitle="Mrs."), self.device)

        guest = Guest.objects.get(pk=GUEST_IN_101)
        self.assertEqual(str(guest.room_id), ROOM_102)
        self.assertEqual(guest.title, "Mrs.")

    def test_unknown_reservation_without_old_room_does_not_touch_the_target_room(self):
        with self.assertRaises(LookupFailure):
            handle_fias(datachange_message(oldRoomName=None, reservationNumber="9999"), self.device)

        # The guest living in the target room must not be stamped with the message
        untouched = Guest.objects.get(pk=GUEST_IN_102)
        self.assertEqual(untouched.name, "Alexandr")
        self.assertIsNone(untouched.additional_info)

    def test_in_place_update_leaves_room_flags_alone(self):
        Guest.objects.filter(pk=GUEST_IN_101).update(additional_info={"pms_reg_num": "4001"})
        Room.objects.filter(pk=ROOM_101).update(state=[Room.CheckedIn, Room.DoNotDisturb])

        handle_fias(datachange_message(roomName="101", oldRoomName=None), self.device)

        # The room row is never saved, so flags make_stable_room_state does not maintain survive
        self.assertEqual(sorted(Room.objects.get(pk=ROOM_101).state), [Room.CheckedIn, Room.DoNotDisturb])
