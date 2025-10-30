from rest_framework import serializers
from users.models import User


class SendLinkParams(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get("email")
        if email:
            attrs["email"] = email.lower()
        try:
            user = User.objects.get(email=attrs["email"], is_active=True)
            attrs["user"] = user
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email not found or is inactive."})
        return attrs
