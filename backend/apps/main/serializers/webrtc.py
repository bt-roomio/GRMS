from rest_framework import serializers


class WebrtcBrokerSerializer(serializers.Serializer):
    gateway_id = serializers.UUIDField()
    ip = serializers.CharField(max_length=255)

    def validate(self, attrs):
        gateway_id = attrs.get("gateway_id")
        ip = (attrs.get("ip") or "").strip()

        if not ip:
            raise serializers.ValidationError({"ip": "ip is required"})

        attrs["gateway_id"] = str(gateway_id)
        attrs["ip"] = ip
        return attrs