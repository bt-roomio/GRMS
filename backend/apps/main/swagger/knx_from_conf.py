from drf_yasg.utils import swagger_auto_schema

from main.serializers.knx_from_conf import KnxDeviceFromConfSerializer


def knx_from_conf_swagger():
    return swagger_auto_schema(
        tags=["Main, Device From Configuration"],
        operation_description="Initialize devices, timeseries and attributes from a KNX configuration",
        request_body=KnxDeviceFromConfSerializer(),
    )
