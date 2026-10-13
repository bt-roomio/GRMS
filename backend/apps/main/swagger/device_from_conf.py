from drf_yasg.utils import swagger_auto_schema

from main.serializers.device_from_conf import DeviceFromConfSerializer


def device_from_conf_swagger():
    return swagger_auto_schema(
        tags=["Main, Device From Configuration"],
        operation_description=(
            "Initialize devices, timeseries and attributes from configuration. "
            "Devices with a room_number are linked to that room; the room and its room_type are created if missing. "
            "floor and block are optional: new rooms default to a floor derived from the number and block 'A'."
        ),
        request_body=DeviceFromConfSerializer(),
        responses={200: DeviceFromConfSerializer()},
    )
