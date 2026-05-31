import logging

from rest_framework import serializers

from access_manager.utilits.cards_public_space import register_cards_for_public_space
from core.utils.serializers import ValidatorSerializer
from main.models import Device, DevicePublicSpaces, PublicSpace
from main.serializers.dashboard import SimpleDashboardSerializer
from main.serializers.device import SimpleDeviceSerializer

logger = logging.getLogger(__name__)


class SimplePublicSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicSpace
        fields = ("id", "name", "floor", "block")


class PublicSpaceSerializer(serializers.ModelSerializer):
    devices = serializers.SerializerMethodField(read_only=True)
    device_ids = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.all(), many=True, required=False, write_only=True
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["dashboard"] = SimpleDashboardSerializer(instance.dashboard).data if instance.dashboard else None
        return data

    def get_devices(self, obj):
        if hasattr(obj, "prefetched_devices"):
            devices = [device_public_space.device for device_public_space in obj.prefetched_devices]
        else:
            devices = Device.objects.filter(device_public_spaces__public_space=obj)

        return SimpleDeviceSerializer(devices, many=True).data

    def update(self, instance, validated_data):
        device_objects = validated_data.pop("device_ids", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if device_objects is not None:
            current_device_relations = DevicePublicSpaces.objects.filter(public_space=instance)
            current_device_ids = list(current_device_relations.values_list("device_id", flat=True))

            incoming_device_ids = [device.id for device in device_objects]

            devices_to_remove = set(current_device_ids) - set(incoming_device_ids)
            devices_to_add = set(incoming_device_ids) - set(current_device_ids)

            if not device_objects:
                devices_to_remove = current_device_ids

            if devices_to_remove:
                register_cards_for_public_space(instance.id, devices_to_remove, False)
                DevicePublicSpaces.objects.filter(public_space=instance, device_id__in=devices_to_remove).delete()

            if devices_to_add:
                device_objects_to_add = [device for device in device_objects if device.id in devices_to_add]
                new_devices = [
                    DevicePublicSpaces(device=device, public_space=instance) for device in device_objects_to_add
                ]
                for d in new_devices:
                    d.full_clean()
                DevicePublicSpaces.objects.bulk_create(new_devices)
                register_cards_for_public_space(instance.id, devices_to_add, True)

        return instance

    def create(self, validated_data):
        device_objects = validated_data.pop("device_ids", [])
        instance = PublicSpace.objects.create(**validated_data)

        if device_objects:
            DevicePublicSpaces.objects.bulk_create(
                [DevicePublicSpaces(device=device, public_space=instance) for device in device_objects]
            )
            devices = [device.id for device in device_objects]
            register_cards_for_public_space(instance.id, devices, True)

        return instance

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
            "device_ids",
            "devices",
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


class PublicSpaceQuickFilterParams(PublicSpaceFilterParams):
    page = None
    size = None
    accessible_for_guest = None
    sort_by = None
    search_field = None
