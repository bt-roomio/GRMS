import logging

from access_manager.models import TypeChoices
from core.management.mq.fias.utils.guests import override_checkout_time
from core.utils.date import unix_to_datetime

logger = logging.getLogger(__name__)

# FIAS field -> Guest.additional_info key, mirrors CheckInSerializer.convert_fields()
_ADDITIONAL_INFO_FIELDS = {
    "reservationNumber": "pms_reg_num",
    "shareFlag": "room_share",
    "swapFlag": "swap_flag",
    "nopost": "no_post",
    "profileNum": "profile_num",
}


def build_reservation_payload(command, data, device):
    tenant_id = device.get("tenant_id")
    return {
        "command": command,
        "tenantId": str(tenant_id),
        "roomNumber": data.get("roomName", "roomNumber"),
        "guestName": data.get("guestName", "guestName"),
        "guestFirstName": data.get("guestFirstName", "guestFirstName"),
        "guestTitle": data.get("guestTitle", "guestTitle"),
        "pmsRegNum": data.get("reservationNumber", "pmsRegNum"),
        "arrivalDateTS": data.get("checkInDate", "arrivalDateTS"),
        "departureDateTS": data.get("checkOutDate", "departureDateTS"),
        "guestLanguage": data.get("language", "guestLanguage"),
        "roomShare": 1 if data.get("shareFlag", "roomShare") else 0,
        "swapFlag": data.get("swapFlag", 0),
        "nopost": data.get("nopost", "nopost"),
        "profileNum": data.get("profileNum", "profileNum"),
        "pin": data.get("pin"),
    }


def build_card_holder_details(holder_type, holder, card_uid):
    if holder_type == "guest":
        additional_info = holder.additional_info or {}
        return {
            "holderType": "guest",
            "roomNumber": holder.room.number if holder.room else "",
            "guestName": holder.name,
            "guestFirstName": holder.lastname or "",
            "guestTitle": holder.title or "",
            "pmsRegNum": additional_info.get("pms_reg_num", ""),
            "arrivalDateTS": holder.check_in,
            "departureDateTS": holder.check_out,
            "guestLanguage": holder.language or "",
            "roomShare": additional_info.get("roomshare", ""),
            "nopost": additional_info.get("no_post", ""),
            "profileNum": additional_info.get("profile_num", ""),
        }

    elif holder_type == "staff":
        group = holder.group
        access_group_name = ""
        group_name = ""
        if group:
            group_name = group.name or ""
            if group.group_type is not None:
                try:
                    access_group_name = TypeChoices(group.group_type).name
                except ValueError:
                    access_group_name = ""
        return {
            "holderType": "staff",
            "cardUid": card_uid,
            "staffName": holder.get_name(),
            "staffFirstName": holder.first_name or "",
            "staffLastName": holder.last_name or "",
            "accessGroup": access_group_name,
            "groupName": group_name,
        }
    return None


def build_guest_move_payload(data, guest, new_room, tenant_id, with_identity=True):
    """Map a FIAS payload onto the keys `handle_guest_move()` reads.

    Only fields actually present in the message are included: `handle_guest_move`
    overwrites whatever key it finds, so a `None` would wipe the stored value.
    `with_identity=False` drops the personal fields, keeping the room and the dates.
    """
    payload = {"room": new_room}

    if with_identity:
        # FIAS sends guestName as "<TITLE> <Surname> <Given name>", guestFirstName as the
        # given name and guestTitle as the normalised salutation. The mapping below is the
        # one CheckInSerializer already uses, kept identical so both paths agree.
        for key, value in (
            ("first_name", data.get("guestName")),
            ("last_name", data.get("guestFirstName")),
            ("language", data.get("language")),
            ("title", data.get("guestTitle")),
        ):
            if isinstance(value, str):
                value = value.strip()
            if value:
                payload[key] = value

    if data.get("checkInDate"):
        payload["check_in_date"] = unix_to_datetime(data["checkInDate"])

    if data.get("checkOutDate"):
        payload["check_out_date"] = unix_to_datetime(override_checkout_time(tenant_id, data["checkOutDate"]))

    check_in = payload.get("check_in_date")
    check_out = payload.get("check_out_date")
    if check_in and check_out and check_out <= check_in:
        logger.warning(
            "datachange guest=%s has checkOut %s not after checkIn %s",
            guest.id,
            check_out,
            check_in,
        )

    additional_info = _merge_additional_info(guest, data)
    if additional_info is not None:
        payload["additional_info"] = additional_info

    return payload


def _merge_additional_info(guest, data):
    merged = dict(guest.additional_info or {})
    changed = False

    for source, target in _ADDITIONAL_INFO_FIELDS.items():
        if source not in data or data[source] is None:
            continue

        value = data[source]
        value = str(1 if value else 0) if source == "shareFlag" else str(value)

        if merged.get(target) != value:
            merged[target] = value
            changed = True

    return merged if changed else None
