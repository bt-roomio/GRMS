import json

from channels_redis.serializers import BaseMessageSerializer


class UUIDSafeJSONSerializer(BaseMessageSerializer):
    """
    JSON serializer for channels_redis that converts uuid.UUID -> str.
    Encryption/decryption stays in the base class (we don't override
    serialize/deserialize, only as_bytes/from_bytes).
    """

    def as_bytes(self, message):
        text = json.dumps(
            message,
            default=str,  # uuid.UUID and anything else json can't encode
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return text.encode("utf-8")

    def from_bytes(self, message: bytes):
        return json.loads(message.decode("utf-8"))
