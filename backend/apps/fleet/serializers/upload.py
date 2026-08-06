from django.conf import settings

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer


class UploadFileSerializer(ValidatorSerializer):
    """
    The file is the whole request. It lands in the node's upload root under its
    own name — there is no destination to choose, so there is none to get wrong.
    """

    file = serializers.FileField()
    mode = serializers.RegexField(r"^0?[0-7]{3}$", required=False, help_text="Octal, e.g. 0644. Defaults to 0644.")
    overwrite = serializers.BooleanField(default=True, help_text="Off means a same-named file is left alone.")

    def validate_file(self, value):
        if value.size is not None and value.size > settings.FLEET_UPLOAD_MAX_BYTES:
            raise serializers.ValidationError(f"File exceeds the {settings.FLEET_UPLOAD_MAX_BYTES} byte limit.")
        return value

    def validate_mode(self, value):
        return int(value, 8)


class UploadResultSerializer(serializers.Serializer):
    path = serializers.CharField(read_only=True)
    size = serializers.IntegerField(read_only=True)
    sha256 = serializers.CharField(read_only=True)
    mode = serializers.CharField(read_only=True)
    replaced = serializers.BooleanField(read_only=True, help_text="True when an existing file was overwritten.")
