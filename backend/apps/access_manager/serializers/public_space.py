from access_manager.models import PublicSpace

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer


class PublicSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicSpace
        fields = (
            "id",
            "created_at",
            "created_by",
            "name",
            "device",
            "tenant",
            "dashboard",
            "additional_info",
        )


class PublicSpaceFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("name", "-name")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
