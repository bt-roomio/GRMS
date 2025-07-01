import logging
from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import PublicSpace
from main.serializers.dashboard import SimpleDashboardSerializer
from main.serializers.device import SimpleDeviceSerializer

logger = logging.getLogger(__name__)


class SimplePublicSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicSpace
        fields = ("id", "name", "floor", "block")


class PublicSpaceSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["device"] = SimpleDeviceSerializer(instance.device).data if instance.device else None
        data["dashboard"] = SimpleDashboardSerializer(instance.dashboard).data if instance.dashboard else None
        return data

    def update(self, instance, validated_data):
        old_device_id = instance.device_id if instance.pk else None

        updated_instance = super().update(instance, validated_data)

        new_device_id = updated_instance.device_id
        if (old_device_id != new_device_id and
                new_device_id and
                updated_instance.device.is_active and
                updated_instance.device.status):
            self._register_cards_for_public_space(updated_instance.id)

        return updated_instance

    def create(self, validated_data):
        instance = super().create(validated_data)

        if (instance.device and
                instance.device.is_active and
                instance.device.status):
            self._register_cards_for_public_space(instance.id)

        return instance

    def _register_cards_for_public_space(self, public_space_id):
        from access_manager.models import GroupPublicSpace
        from access_manager.tasks import card_public_space

        try:
            group_public_spaces = GroupPublicSpace.objects.filter(
                public_space_id=public_space_id,
                group__is_active=True
            ).select_related('group')

            for group_public_space in group_public_spaces:
                try:
                    card_public_space(
                        group_id=group_public_space.group_id,
                        public_space_id=public_space_id,
                        action="connect"
                    )
                except Exception as e:
                    logger.error(
                        "Error registering cards for group %s to public space %s: %s",
                        group_public_space.group_id,
                        public_space_id,
                        str(e)
                    )

        except Exception as e:
            logger.error(
                "Error in _register_cards_for_public_space for public space %s: %s",
                public_space_id,
                str(e)
            )

    class Meta:
        model = PublicSpace
        fields = (
            "id",
            "created_at",
            "created_by",
            "name",
            "floor",
            "block",
            "accessible_for_guest",
            "device",
            "tenant",
            "dashboard",
            "additional_info",
        )


class PublicSpaceFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("name", "-name")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=(["name"]), required=False)
    search_value = serializers.CharField(required=False)
    accessible_for_guest = serializers.BooleanField(required=False, allow_null=True, default=None)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
