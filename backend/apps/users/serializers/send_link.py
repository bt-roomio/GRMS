from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from users.models import User


class SendLinkParams(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get("email")
        if email:
            attrs["email"] = email.lower()
        user = get_object_or_404(User, email=attrs["email"])
        attrs["user"] = user
        return attrs
