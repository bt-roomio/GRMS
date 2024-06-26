from rest_framework import serializers

from shuttle.models import AttributeKv
from main.models import Device


class AttributeKvSerializer(serializers.Serializer):
    # TODO: here need custom is_valid method for getting request.data dynamically!
    def update(self, instance, validated_data):
        print(instance, validated_data, "update")
        return instance

    def create(self, validated_data):
        print(validated_data, "create")
        return AttributeKv.objects.create(**validated_data)


class AttributeKvParams(serializers.Serializer):
    deviceId = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    scope = serializers.ChoiceField(choices=[AttributeKv.SHARED_SCOPE, AttributeKv.SERVER_SCOPE])
