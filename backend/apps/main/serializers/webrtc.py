# from rest_framework import serializers
#
# class WebrtcBrokerSerializer(serializers.Serializer):
#     agent_id = serializers.CharField(max_length=128)
#     ip = serializers.CharField(max_length=255, help_text="IPv4/IPv6 or host, optionally with :port")
#
#     def validate(self, attrs):
#         agent_id = (attrs.get("agent_id") or "").strip()
#         ip = (attrs.get("ip") or "").strip()
#
#         if not agent_id:
#             raise serializers.ValidationError({"agent_id": "agent_id is required"})
#         if not ip:
#             raise serializers.ValidationError({"ip": "ip is required"})
#
#         attrs["agent_id"] = agent_id
#         attrs["ip"] = ip
#         return attrs


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