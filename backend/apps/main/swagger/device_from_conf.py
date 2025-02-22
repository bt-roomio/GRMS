from drf_yasg.utils import swagger_auto_schema

from main.serializers.device_from_conf import DeviceFromConfSerializer


def device_from_conf_swagger():
    return swagger_auto_schema(
        tags=["Main, Device From Configuration"],
        operation_description="Initialize devices, timeseries and attributes from configuration",
        request_body=DeviceFromConfSerializer(),
    )
