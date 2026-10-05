import json
import uuid

from channels_redis.serializers import BaseMessageSerializer


class UUIDSafeJSONSerializer(BaseMessageSerializer):
    """
    JSON-сериалайзер для channels_redis, который переводит uuid.UUID -> str.
    Шифрование/дешифрование останется на базовом классе (мы не переопределяем
    serialize/deserialize, только as_bytes/from_bytes).
    """

    def as_bytes(self, message):
        def default(o):
            if isinstance(o, uuid.UUID):
                return str(o)
            return str(o)

        text = json.dumps(
            message,
            default=default,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return text.encode("utf-8")

    def from_bytes(self, message: bytes):
        return json.loads(message.decode("utf-8"))
