from rest_framework import serializers

from main.models import EmailConfiguration, Tenant


class EmailConfigSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)

    class Meta:
        model = EmailConfiguration
        fields = ('id', 'tenant', 'email', 'host', 'username', 'password', 'port', 'use_tls')
