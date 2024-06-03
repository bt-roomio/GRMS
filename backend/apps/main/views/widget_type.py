from main.models import WidgetType
from main.serializers.widget_type import WidgetTypeFilterParams, WidgetTypeSerializer
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView, Response

from apps.core.utils.pagination import pagination


class WidgetTypeListView(APIView):
	def get(self, request):
		params = WidgetTypeFilterParams.check(request.GET)
		instance = WidgetType.objects.filter(tenant_id=request.user.tenant_id)
		serializer = WidgetTypeSerializer(instance, many=True)
		data = pagination(instance, serializer, params.get("page"), params.get("size"))
		return Response(data)
