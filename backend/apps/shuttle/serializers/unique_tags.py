from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from shuttle.models import AttributeKv


class UniqueTagsFilterParams(ValidatorSerializer):
    tag_type = serializers.ChoiceField(choices=["telemetry", "attributes"])
    attribute_scope = serializers.ChoiceField(
        choices=[AttributeKv.CLIENT_SCOPE, AttributeKv.SERVER_SCOPE, AttributeKv.SHARED_SCOPE],
        required=False,
    )
    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=15, min_value=1, max_value=500)

    def validate(self, attrs):
        if attrs.get("tag_type") == "attributes" and not attrs.get("attribute_scope"):
            raise serializers.ValidationError(
                {"attribute_scope": "This field is required when tag_type is 'attributes'."}
            )
        return attrs
