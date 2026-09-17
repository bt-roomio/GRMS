from rest_framework import serializers

from users.models import User


class SendLinkParams(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get("email")
        if email:
            attrs["email"] = email.lower()

        # A missing user is not a validation error: the view answers identically
        # in both cases so that account existence is not disclosed.
        attrs["user"] = User.objects.filter(email=attrs["email"], is_active=True).first()
        return attrs
