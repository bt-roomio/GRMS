from rest_framework import serializers


PIN_MIN_LENGTH = 4
PIN_MAX_LENGTH = 10


def _is_simple_pin(pin: str) -> bool:
    if len(set(pin)) == 1:
        return True

    deltas = {int(b) - int(a) for a, b in zip(pin, pin[1:])}
    return deltas in ({1}, {-1})


class GuestCardRequestSerializer(serializers.Serializer):
    guest_id = serializers.CharField()
    cards = serializers.ListField(
        child=serializers.CharField(), max_length=10, error_messages={"max_length": "Maximum 10 cards allowed"}
    )
    public_spaces = serializers.ListField(child=serializers.CharField(), required=False, default=[])
    is_pwd = serializers.BooleanField(required=False, default=False)

    def validate_cards(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 cards allowed")
        return value

    def validate(self, attrs):
        if attrs.get("is_pwd") and attrs.get("cards"):
            attrs["cards"] = attrs["cards"][:1]
            pin = attrs["cards"][0]

            if not pin.isdigit() or not PIN_MIN_LENGTH <= len(pin) <= PIN_MAX_LENGTH:
                raise serializers.ValidationError({"cards": f"PIN must be {PIN_MIN_LENGTH}-{PIN_MAX_LENGTH} digits."})

            if _is_simple_pin(pin):
                raise serializers.ValidationError({"cards": "PIN is too simple. Avoid repeated or sequential digits."})

        return attrs
