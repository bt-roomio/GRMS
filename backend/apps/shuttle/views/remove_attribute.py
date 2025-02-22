from rest_framework.response import Response
from rest_framework.views import APIView

from shuttle.models import AttributeKv
from shuttle.serializers.remove_attribute import RemoveAttributeFilterParams, RemoveAttributeFilterPath
from shuttle.swagger.remove_attribute import remove_attribute_swagger


class RemoveAttribute(APIView):
    @remove_attribute_swagger()
    def delete(self, request, *args, **kwargs):
        path = RemoveAttributeFilterPath.check(kwargs)
        params = RemoveAttributeFilterParams.check(request.GET)
        attrs = AttributeKv.objects.filter(
            entity_id=path.get("device_id"),
            attribute_type=path.get("scope"),
            attribute_key__in=params.get("keys", "")[0].split(","),
        )
        if not attrs:
            return Response({"detail": "Not found these keys!"}, 404)

        will_remove = list(attrs.values_list("attribute_key", flat=True))
        attrs.delete()
        return Response({"message": f"Removed {will_remove}"})
