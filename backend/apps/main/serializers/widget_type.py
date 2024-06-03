from main.models import WidgetType
from rest_framework import serializers

from apps.core.utils.serializers import ValidatorSerializer


class WidgetTypeSerializer(serializers.ModelSerializer):
	class Meta:
		model = WidgetType
		fields = (
			"id",
			"created_at",
			"name",
			"tenant",
			"deprecated",
			"fqn",
			"descriptor",
			"image",
			"description",
			"tags",
			"external_id",
		)


class WidgetTypeFilterParams(ValidatorSerializer):
	page = serializers.IntegerField(default=1)
	size = serializers.IntegerField(default=50)
