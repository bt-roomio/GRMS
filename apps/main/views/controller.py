from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device
from main.serializers.controller import ControllerFilterPath
from main.swagger.controller import swagger
from shuttle.models import AttributeKv


class ControllerListView(APIView):
    @swagger()
    def get(self, request, *args, **kwargs):
        try:
            result = []
            path = ControllerFilterPath.check(kwargs)
            device = get_object_or_404(Device, id=path.get("device_id").id, additional_info__gateway=True)
            attrs = get_object_or_404(
                AttributeKv, entity=device, attribute_type=AttributeKv.SHARED_SCOPE, attribute_key=path.get("name")
            )
            configuration_json = attrs.json_v and attrs.json_v.get("configurationJson") or {}
            devices = configuration_json.get("devices") or {}
            address_maps = {
                i.get("addressMapId"): i.get("addressMapName") for i in configuration_json.get("addressMaps")
            }
            temp_devices = [i.get("macAddress") for i in devices if i.get("tempDevice")]
            not_temp_devices = list(filter(lambda x: not x.get("tempDevice"), devices))
            self.get_scanned_devices(temp_devices, not_temp_devices, address_maps, result)
            self.get_gateway_attrs(not_temp_devices, address_maps, result)

            return Response(result)
        except Exception as e:
            return Response({"detail": str(e)}, 400)

    @staticmethod
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
                    "addressMapId": i.get("addressMapId")
                    for i in not_temp_devices
                    if mac_address == i.get("macAddress")
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

    @staticmethod
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
