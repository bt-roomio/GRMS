from channels.db import database_sync_to_async

from main.models import Device
from shuttle.models import AttributeKv
from shuttle.utils.response import response


@database_sync_to_async
def get_device(cmd, user):
    return Device.objects.filter(id=cmd.get("entityId"), additional_info__gateway=True, tenant=user.tenant).first()


@database_sync_to_async
def get_attributes(cmd, device):
    return AttributeKv.objects.filter(
        entity=device,
        attribute_type=AttributeKv.SHARED_SCOPE,
        attribute_key=cmd.get("connectorName"),
    ).first()


async def main_scanned_devices(cmd, connectors, user):
    device = await get_device(cmd, user)
    attrs = await get_attributes(cmd, device)
    configuration_json = attrs and attrs.json_v and attrs.json_v.get("configurationJson") or {}
    devices = configuration_json.get("devices") or {}
    address_maps = {i.get("addressMapId"): i.get("addressMapName") for i in configuration_json.get("addressMaps", {})}
    temp_devices = [i.get("macAddress") for i in devices if i.get("tempDevice")]
    not_temp_devices = list(filter(lambda x: not x.get("tempDevice"), devices))

    scanned_devices = await get_scanned_devices(temp_devices, not_temp_devices, address_maps)
    gateway_devices = await get_gateway_attrs(not_temp_devices, address_maps, scanned_devices)
    upload_status, scan_status = await get_upload_scan_statuses(temp_devices)

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
            address_map = address_maps[address_map_id.get("addressMapId")] if address_map_id else None
            print(address_map)
            found_device = Device.objects.filter(name=mac_address).first()
            data = {
                "mac_address": mac_address,
                "ip_address": value.get("ip"),
                "room": found_device and str(found_device.room),
                "address_map": (
                    {"id": address_map_id.get("addressMapId"), "name": address_map}
                    if address_map_id.get("addressMapId")
                    else None
                ),
                "file": "",
                "status": value.get("device_is_online"),
                "exist_in_configuration": True,
                "upload_file_status": value.get("upload_file_status"),
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
            "exist_in_configuration": False,
            "upload_file_status": None,
        }
        result.append(data)

    return result


aa = {
    "id": "79f4bc2c-a9e5-48d7-be5b-d375b9a6d471",
    "ts": 1731914125571,
    "name": "Roomio Connector",
    "type": "roomio",
    "grpc_key": None,
    "logLevel": "DEBUG",
    "configuration": "Roomio Connector.json",
    "configurationJson": {
        "id": "79f4bc2c-a9e5-48d7-be5b-d375b9a6d471",
        "name": "Roomio Connector",
        "server": {
            "host": "0.0.0.0",
            "name": "HRC350 connector",
            "port": "51003",
            "clientId": "ThingsBoard_gateway",
            "logLevel": "DEBUG",
            "pollPeriod": 3,
            "maxNumberOfWorkers": 100,
            "sendDataOnlyOnChange": True,
            "maxMessageNumberPerWorker": 10,
        },
        "devices": [
            {"macAddress": "HRC350_HIHOerowNf", "tempDevice": True},
            {"lastIP": "192.168.0.1", "macAddress": "28:87:ba:e4:1f:f2", "addressMapId": 1},
            {"lastIP": "192.168.0.105", "macAddress": "fc:e8:92:2e:2d:cb", "addressMapId": 2},
            {"lastIP": "192.168.0.120", "macAddress": "24:3e:b2:da:d3:e3", "addressMapId": 23},
        ],
        "logLevel": "DEBUG",
        "addressMaps": [
            {
                "attributes": [
                    {"tag": "dnd", "address": 16554, "group_address": "8/0/170"},
                    {"tag": "DND Relay DO01", "address": 1, "group_address": "0/0/1"},
                    {"tag": "AC_status", "address": 16552, "group_address": "8/0/168"},
                    {"tag": "current_temp", "address": 16551, "group_address": "8/0/167"},
                    {"tag": "mur", "address": 16553, "group_address": "8/0/169"},
                ],
                "timeseries": [
                    {"tag": "dnd", "address": 16554, "group_address": "8/0/170"},
                    {"tag": "DND Relay DO01", "address": 1, "group_address": "0/0/1"},
                    {"tag": "AC_status", "address": 16552, "group_address": "8/0/168"},
                    {"tag": "current_temp", "address": 16551, "group_address": "8/0/167"},
                    {"tag": "mur", "address": 16553, "group_address": "8/0/169"},
                ],
                "addressMapId": 1,
                "addressMapName": "Standart Room",
                "attributeUpdates": [
                    {"tag": "AC_max_temp", "address": 16554, "group_address": "8/0/170"},
                    {"tag": "temp", "address": 13500, "group_address": "6/4/188"},
                    {"tag": "AC_min_temp", "address": 16554, "group_address": "8/0/170"},
                ],
            },
            {
                "attributes": [],
                "timeseries": [
                    {"tag": "dnd", "address": 16554, "group_address": "8/0/170"},
                    {"tag": "AC_status", "address": 16552, "group_address": "8/0/168"},
                    {"tag": "current_temp", "address": 16551, "group_address": "8/0/167"},
                    {"tag": "mur", "address": 16553, "group_address": "8/0/169"},
                ],
                "addressMapId": 2,
                "addressMapName": "Luxury Room",
                "attributeUpdates": [
                    {"tag": "AC_max_temp", "address": 16554, "group_address": "8/0/170"},
                    {"tag": "AC_min_temp", "address": 16554, "group_address": "8/0/170"},
                ],
            },
            {
                "attributes": [
                    {"tag": "dnd", "address": 16554, "group_address": "8/0/170"},
                    {"tag": "DND Relay DO01", "address": 1, "group_address": "0/0/1"},
                    {"tag": "AC_status", "address": 16552, "group_address": "8/0/168"},
                    {"tag": "current_temp", "address": 16551, "group_address": "8/0/167"},
                    {"tag": "mur", "address": 16553, "group_address": "8/0/169"},
                ],
                "timeseries": [
                    {"tag": "dnd", "address": 16554, "group_address": "8/0/170"},
                    {"tag": "DND Relay DO01", "address": 1, "group_address": "0/0/1"},
                    {"tag": "AC_status", "address": 16552, "group_address": "8/0/168"},
                    {"tag": "current_temp", "address": 16551, "group_address": "8/0/167"},
                    {"tag": "mur", "address": 16553, "group_address": "8/0/169"},
                ],
                "addressMapId": 3,
                "addressMapName": "Standart Room (copy 1)",
                "attributeUpdates": [
                    {"tag": "AC_max_temp", "address": 16554, "group_address": "8/0/170"},
                    {"tag": "temp", "address": 13500, "group_address": "6/4/188"},
                    {"tag": "AC_min_temp", "address": 16554, "group_address": "8/0/170"},
                ],
            },
            {
                "attributes": [],
                "timeseries": [
                    {"tag": "DND", "address": 1, "group_address": "0/0/1"},
                    {"tag": "MUR", "address": 2, "group_address": "0/0/2"},
                    {"tag": "AC_ON_OFF", "address": 23051, "group_address": "11/2/11"},
                    {"tag": "DND Relay", "address": 3, "group_address": "0/0/3"},
                    {"tag": "MUR Relay", "address": 4, "group_address": "0/0/4"},
                    {"tag": "Room Temperature", "address": 5, "group_address": "0/0/5"},
                ],
                "addressMapId": 23,
                "addressMapName": "test",
                "attributeUpdates": [
                    {"tag": "Test", "address": 1, "group_address": "0/0/1"},
                    {"tag": "11", "address": 1234, "group_address": "0/4/210"},
                    {"tag": "Check-in date", "address": 6, "group_address": "0/0/6"},
                    {"tag": "Check-out date", "address": 7, "group_address": "0/0/7"},
                ],
            },
            {
                "attributes": [],
                "timeseries": [{"tag": "jjj", "address": 1111, "group_address": "0/4/87"}],
                "addressMapId": 24,
                "addressMapName": "Test address map delete address map id",
                "attributeUpdates": [],
            },
        ],
        "enableRemoteLogging": True,
    },
}


bb = {
    "20:8d:4f:02:93:25": {"ip": "192.168.0.128", "device_is_online": False},
    "24:3e:b2:da:d3:e3": {"ip": "192.168.0.120", "device_is_online": True, "upload_file_status": 2},
    "84:10:58:5a:61:46": {"ip": "192.168.0.125", "device_is_online": False},
    "bc:e3:5c:0e:d3:e4": {"ip": "192.168.0.148", "device_is_online": False},
    "e0:58:5c:0e:d3:e4": {"ip": "192.168.0.57", "device_is_online": False},
}
