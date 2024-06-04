import json

from rest_framework import serializers


class AlarmSettingsSerializer(serializers.Serializer):
	bathroom_enable = serializers.BooleanField()
	humidity_enable = serializers.BooleanField()

	def update(self, instance, validated_data):
		instance.additional_info = json.dumps({"general_settings": validated_data})
		instance.save()
		return instance

	def to_representation(self, instance):
		return {"tenant_id": instance.id, **self.validated_data}
