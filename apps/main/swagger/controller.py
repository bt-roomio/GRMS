from drf_yasg.utils import swagger_auto_schema


def swagger():
    return swagger_auto_schema(
        responses={
            200: "List of controllers.",
            400: '{"detail": "Error message!"}',
        }
    )
