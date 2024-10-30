from channels.db import database_sync_to_async

from main.models import Device
from shuttle.models import AttributeKv
from shuttle.utils.response import response


async def main_scanned_devices(get_object_or_404_ws, cmd, connectors):
    device = await get_object_or_404_ws(Device, id=cmd.get("entityId"), additional_info__gateway=True)
    attrs = await get_object_or_404_ws(
        AttributeKv,
        entity=device,
        attribute_type=AttributeKv.SHARED_SCOPE,
        attribute_key=cmd.get("connectorName"),
    )
    configuration_json = attrs and attrs.json_v and attrs.json_v.get("configurationJson") or {}
    devices = configuration_json.get("devices") or {}
    address_maps = {i.get("addressMapId"): i.get("addressMapName") for i in configuration_json.get("addressMaps")}
    temp_devices = [i.get("macAddress") for i in devices if i.get("tempDevice")]
    not_temp_devices = list(filter(lambda x: not x.get("tempDevice"), devices))

    scanned_devices = await get_scanned_devices(temp_devices, not_temp_devices, address_maps)
    gateway_devices = await get_gateway_attrs(not_temp_devices, address_maps, scanned_devices)

    if not connectors:
        connectors = [*scanned_devices, *gateway_devices]

    page_link = cmd.get("query", {}).get("pageLink")
    page = page_link.get("page") or 1
    page_size = page_link.get("pageSize")
    offset = (page - 1) * page_size
    limit = offset + page_size
    count = len(connectors)
    page_link["count"] = count

    result = response({}, cmd.get("cmdId"))
    result["data"]["connectors"] = connectors[offset:limit]
    result["data"]["query"] = cmd.get("query")
    return result


@database_sync_to_async
def get_scanned_devices(temp_devices, not_temp_devices, address_maps):
    result = []
    attrs = (
        AttributeKv.objects.select_related("entity")
        .filter(
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
            address_map = address_maps[address_map_id.get("addressMapId")] if address_map_id else {}
            found_device = Device.objects.filter(name=mac_address).first()
            data = {
                "mac_address": mac_address,
                "ip_address": value.get("ip"),
                "room": found_device and str(found_device.room),
                "address_map": {"id": address_map_id.get("addressMapId"), "name": address_map},
                "file": "",
                "status": value.get("device_is_online"),
            }
            result.append(data)
    return result


@database_sync_to_async
def get_gateway_attrs(not_temp_devices, address_maps, scanned_devices):
    result = []
    for device in not_temp_devices:
        if bool(list(filter(lambda x: x.get("mac_address") == device.get("macAddress"), scanned_devices))):
            continue
        found_device = Device.objects.filter(name=device.get("macAddress")).first()
        address_map = address_maps.get(device.get("addressMapId"), None)
        data = {
            "mac_address": device.get("macAddress"),
            "ip_address": device.get("lastIp"),
            "room": found_device and str(found_device.room),
            "address_map": {"id": device.get("addressMapId"), "name": address_map},
            "file": "",
            "status": False,
        }
        result.append(data)

    return result
