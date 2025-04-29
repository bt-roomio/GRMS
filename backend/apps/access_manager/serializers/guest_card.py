from rest_framework import serializers


class GuestCardRequestSerializer(serializers.Serializer):
    guest_id = serializers.CharField()
    cards = serializers.ListField(
        child=serializers.CharField(), max_length=10, error_messages={"max_length": "Maximum 10 cards allowed"}
    )
    public_spaces = serializers.ListField(child=serializers.CharField(), required=False, default=[])

    def validate_cards(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 cards allowed")
        return value
