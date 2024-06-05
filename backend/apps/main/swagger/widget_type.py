from drf_yasg import openapi
from main.serializers.widget_type import WidgetTypeSerializer

WidgetTypeSwagger = {
	200: openapi.Response(
		description="Success",
		examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
		schema=WidgetTypeSerializer,
	),
}

WidgetTypeDetailSwagger = {200: WidgetTypeSerializer}
