from channels.db import database_sync_to_async

from main.models import Device
from shuttle.models import AttributeKv, Controller
from shuttle.utils.response import response


@database_sync_to_async
def get_device(entity_id, user):
    return Device.objects.filter(id=entity_id, additional_info__gateway=True, tenant=user.tenant).first()


@database_sync_to_async
def get_attributes(connector_name, device):
    return AttributeKv.objects.filter(
        entity=device,
        attribute_type=AttributeKv.SHARED_SCOPE,
        attribute_key=connector_name,
    ).first()


async def main_scanned_devices(cmd, connectors, user):
    result = response(
        {"devices": [], "upload_status": False, "scan_status": False, "query": cmd.get("query")}, cmd.get("cmd_id")
    )
    device = await get_device(cmd.get("entity_id"), user)
    if not device:
        return result
    attrs = await get_attributes(cmd.get("connector_name"), device)

    configuration_json = attrs and attrs.json_v and attrs.json_v.get("configurationJson") or {}
    devices = configuration_json.get("devices") or {}
    address_maps = {i.get("addressMapId"): i.get("addressMapName") for i in configuration_json.get("addressMaps", {})}
    temp_devices = [i.get("macAddress") for i in devices if i.get("tempDevice")]
    not_temp_devices = list(filter(lambda x: not x.get("tempDevice"), devices))

    scanned_devices = await get_scanned_devices(temp_devices, not_temp_devices, address_maps, user)
    gateway_devices = await get_gateway_attrs(not_temp_devices, address_maps, scanned_devices, user)
    upload_status, scan_status = await get_upload_scan_statuses(temp_devices)

    if not connectors:
        connectors = [*scanned_devices, *gateway_devices]

    filter_room_type = cmd.get("query", {}).get("filters", {}).get("room_type")
    if filter_room_type:
        connectors = [con for con in connectors if con.get("room_type") == filter_room_type]

    page_link = cmd.get("query", {}).get("page_link")
    page = page_link.get("page") or 1
    page_size = page_link.get("size", 10)
    offset = (page - 1) * page_size
    limit = offset + page_size
    count = len(connectors)
    page_link["count"] = count

    result["data"]["devices"] = connectors[offset:limit]
    result["data"]["upload_status"] = upload_status
    result["data"]["scan_status"] = scan_status
    result["data"]["query"] = cmd.get("query")
    return result


@database_sync_to_async
def get_upload_scan_statuses(temp_devices):
    upload_status = AttributeKv.objects.filter(
        entity__name__in=temp_devices,
        attribute_type=AttributeKv.CLIENT_SCOPE,
        attribute_key="upload_status",
    ).first()
    scan_status = AttributeKv.objects.filter(
        entity__name__in=temp_devices,
        attribute_type=AttributeKv.CLIENT_SCOPE,
        attribute_key="scan_status",
    ).first()
    upload_status = upload_status and upload_status.bool_v
    scan_status = scan_status and scan_status.bool_v
    return upload_status, scan_status


@database_sync_to_async
def get_scanned_devices(temp_devices, not_temp_devices, address_maps, user):
    result = []
    attrs = (
        AttributeKv.objects.select_related("entity")
        .filter(
            entity__tenant=user.tenant,
            entity__name__in=temp_devices,
            attribute_type=AttributeKv.CLIENT_SCOPE,
            attribute_key="scanned_devices",
        )
        .values("json_v")
    )
    for scan_device in attrs:
        scan_device = scan_device.get("json_v")
        for mac_address, value in scan_device.items():
            address_map_id = {
                "addressMapId": i.get("addressMapId") for i in not_temp_devices if mac_address == i.get("macAddress")
            }
            address_map = address_maps[address_map_id.get("addressMapId")] if address_map_id else None
            found_device = Device.objects.is_active().filter(name=mac_address, tenant=user.tenant).first()
            controller = Controller.objects.filter(mac_address=mac_address).last()
            data = {
                "mac_address": mac_address,
                "ip_address": value.get("ip"),
                "room": found_device and found_device.room and found_device.room.number,
                "room_type": found_device
                and found_device.room
                and found_device.room.type
                and found_device.room.type.title,
                "address_map": (
                    {"id": address_map_id.get("addressMapId"), "name": address_map}
                    if address_map_id.get("addressMapId")
                    else None
                ),
                "file": controller and controller.file.content.name,
                "status": value.get("device_is_online"),
                "exist_in_configuration": False,
                "upload_file_status": value.get("upload_file_status"),
            }
            result.append(data)
    return result


@database_sync_to_async
def get_gateway_attrs(not_temp_devices, address_maps, scanned_devices, user):
    result = []
    for device in not_temp_devices:
        if bool(list(filter(lambda x: x.get("mac_address") == device.get("macAddress"), scanned_devices))):
            for x in scanned_devices:
                if x.get("mac_address") == device.get("macAddress"):
                    x["exist_in_configuration"] = True
            continue
        found_device = Device.objects.is_active().filter(name=device.get("macAddress"), tenant=user.tenant).first()
        address_map = address_maps.get(device.get("addressMapId"), None)
        controller = Controller.objects.filter(mac_address=device.get("macAddress")).last()
        data = {
            "mac_address": device.get("macAddress"),
            "ip_address": device.get("lastIp"),
            "room": found_device and found_device.room and found_device.room.number,
            "address_map": {"id": device.get("addressMapId"), "name": address_map},
            "file": controller and controller.file.content.path,
            "status": False,
            "exist_in_configuration": True,
            "upload_file_status": None,
        }
        result.append(data)

    return result
