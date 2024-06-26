from rest_framework.views import APIView, Response

from shuttle.models import AttributeKv
from shuttle.serializers.attributes import AttributeKvParams, AttributeKvSerializer


class AttributeListView(APIView):
    def post(self, request, *args, **kwargs):
        params = AttributeKvParams(data=kwargs)
        params.is_valid(raise_exception=True)

        instance = AttributeKv.objects.filter(
            entity_id=params.validated_data.get("deviceId"), attribute_type=params.validated_data.get("scope")
        )
        print(instance, request.data)
        serializer = AttributeKvSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()
