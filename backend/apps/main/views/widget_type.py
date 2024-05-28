from rest_framework.generics import ListAPIView

from main.models import WidgetType
from main.serializers.widget_type import WidgetTypeSerializer


class WidgetTypeListView(ListAPIView):
    queryset = WidgetType.objects.all()
    serializer_class = WidgetTypeSerializer
