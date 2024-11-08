from rest_framework import serializers

from shuttle.models import ControllerFile


class ControllerFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControllerFile
        fields = ("id", "content", "file_type")
