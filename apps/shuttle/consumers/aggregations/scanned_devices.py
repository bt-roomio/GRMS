from channels.db import database_sync_to_async

from main.models import Device
from shuttle.models import AttributeKv


@database_sync_to_async
def get_scanned_devices(temp_devices, not_temp_devices, address_maps, result):
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
                "address_map": address_map,
                "file": "",
                "status": value.get("device_is_online"),
            }
            result.append(data)


@database_sync_to_async
def get_gateway_attrs(not_temp_devices, address_maps, result):
    for device in not_temp_devices:
        found_device = Device.objects.filter(name=device.get("macAddress")).first()
        address_map = address_maps[device.get("addressMapId")]
        data = {
            "mac_address": device.get("macAddress"),
            "ip_address": device.get("lastIp"),
            "room": found_device and str(found_device.room),
            "address_map": address_map,
            "file": "",
            "status": False,
        }
        result.append(data)
