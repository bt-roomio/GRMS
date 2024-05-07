from rest_framework import serializers

from main.models import AdminSettings, Tenant


class ChangeEmailConfigSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)

    def create(self, validated_data):
        request = self.context.get('request')

        if not request:
            raise serializers.ValidationError({"detail": "Send `request` from view!"})

        if not request.user.tenant_id:
            raise serializers.ValidationError({"detail": "Tenant not found!"})

        instance, _ = AdminSettings.objects.update_or_create(
            tenant=request.user.tenant,
            key=validated_data["key"],
            defaults={
                'json_value': validated_data.get("json_value", {})
            }
        )
        return instance

    class Meta:
        model = AdminSettings
        fields = ('id', 'tenant', 'key', 'json_value')
