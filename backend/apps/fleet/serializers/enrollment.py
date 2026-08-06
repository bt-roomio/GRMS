from rest_framework import serializers


class InstallCommandSerializer(serializers.Serializer):
    install_url = serializers.CharField(read_only=True, help_text="One-time link that serves the bootstrap script.")
    command = serializers.CharField(read_only=True, help_text="curl … | sudo bash — needs the VM to reach this server.")
    hostname = serializers.CharField(read_only=True, help_text="The NetBird peer name this node will register as.")
    peer_replaced = serializers.BooleanField(
        read_only=True,
        help_text="True when an existing peer and its setup key were deleted to make room for this one.",
    )
    expires_at = serializers.IntegerField(read_only=True)
