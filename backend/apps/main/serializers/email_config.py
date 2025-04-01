from main.models import EmailConfiguration, Tenant
from rest_framework import serializers


class EmailConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailConfiguration
        fields = (
            "id",
            "tenant",
            "email",
            "host",
            "username",
            "password",
            "port",
            "use_tls",
            "frontend_host",
            "frontend_port",
        )
        extra_kwargs = {"id": {"required": False}, "tenant": {"required": False}, "email": {"required": False},
                        "host": {"required": False}, "username": {"required": False}, "password": {"required": False},
                        "port": {"required": False}, "use_tls": {"required": False}}
