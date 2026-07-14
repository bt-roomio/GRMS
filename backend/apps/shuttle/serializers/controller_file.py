from rest_framework import serializers
from rest_framework.fields import RegexValidator

from core.utils.serializers import ValidatorSerializer
from shuttle.models import Controller, ControllerFile


class ControllerFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControllerFile
        fields = ("id", "content", "file_type")


class ControllerSerializer(serializers.ModelSerializer):
    file_type = serializers.CharField(source="file.file_type", read_only=True)
    file_path = serializers.FileField(source="file.content", read_only=True)

    class Meta:
        model = Controller
        fields = ("id", "created_at", "mac_address", "tenant", "file_type", "file_path")


class ControllerLegacySerializer(serializers.Serializer):
    controllers = serializers.ListField(
        child=serializers.CharField(
            max_length=17,
            validators=[
                RegexValidator("(?:[0-9a-fA-F]:?){12}", message="Controllers should include only mac_addresses"),
            ],
        ),
        write_only=True,
    )
    file = serializers.FileField()
    file_type = serializers.CharField(max_length=255, default="firmware")

    def create(self, validated_data):
        tenant_id = self.context.get("tenant_id")

        mac_addresses = validated_data.get("controllers", [])
        file = validated_data.get("file")
        file_type = validated_data.get("file_type")

        controller_file = ControllerFile.objects.create(content=file, tenant_id=tenant_id, file_type=file_type)
        controller_file_serializer = ControllerFileSerializer(controller_file)
        data = {"controllers": [], "file": controller_file_serializer.data}

        for mac_address in mac_addresses:
            Controller.objects.create(
                mac_address=mac_address,
                tenant_id=tenant_id,
                file_id=controller_file.id,
            )
            data["controllers"].append(mac_address)
        return data


class ControllerParams(ValidatorSerializer):
    SORT_FIELDS = (
        "created_at",
        "-created_at",
    )

    size = serializers.IntegerField(default=50, max_value=500)
    page = serializers.IntegerField(default=1, min_value=1)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
    search_value = serializers.CharField(required=False, allow_null=True)
    file_type = serializers.CharField(required=False, allow_null=True)
