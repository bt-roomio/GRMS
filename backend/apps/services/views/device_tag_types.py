from rest_framework.generics import get_object_or_404
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from main.models import Device
from services.serializers.device_tag_types import TAG_TYPES_KEY, DeviceTagTypeSerializer
from services.swagger.device_tag_types import device_tag_types_swagger_retrieve, device_tag_types_swagger_update
from shuttle.models import AttributeKv


class DeviceTagTypesView(APIView):
    """The device's tag types, kept as one JSON list in its ``TAG_TYPES`` SERVER_SCOPE attribute."""

    parser_classes = (JSONParser,)

    def get_own_device(self, request, device_id):
        return get_object_or_404(Device.objects.filter(tenant_id=request.user.tenant_id), pk=device_id)

    @device_tag_types_swagger_retrieve()
    @check_perms(["shuttle.view_attributelist"])
    def get(self, request, device_id):
        device = self.get_own_device(request, device_id)
        attribute = AttributeKv.objects.filter(
            entity=device, attribute_type=AttributeKv.SERVER_SCOPE, attribute_key=TAG_TYPES_KEY
        ).first()
        return Response(attribute.json_v or [] if attribute else [])

    @device_tag_types_swagger_update()
    @check_perms(["shuttle.add_attributelist"])
    def post(self, request, device_id):
        return self.save(request, device_id)

    @device_tag_types_swagger_update()
    @check_perms(["shuttle.add_attributelist"])
    def put(self, request, device_id):
        return self.save(request, device_id)

    def save(self, request, device_id):
        """Replace the device's ``TAG_TYPES`` with the request list (POST and PUT alike)."""
        device = self.get_own_device(request, device_id)
        serializer = DeviceTagTypeSerializer(
            data=request.data, many=True, context={"tenant_id": request.user.tenant_id}
        )
        serializer.is_valid(raise_exception=True)
        tag_types = [dict(item) for item in serializer.validated_data]
        AttributeKv.objects.update_or_create(
            entity=device,
            attribute_type=AttributeKv.SERVER_SCOPE,
            attribute_key=TAG_TYPES_KEY,
            defaults={
                "entity_type": "DEVICE",
                "bool_v": None,
                "str_v": None,
                "long_v": None,
                "dbl_v": None,
                "json_v": tag_types,
            },
        )
        return Response(tag_types)
