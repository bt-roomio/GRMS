from access_manager.models import TypeChoices


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
