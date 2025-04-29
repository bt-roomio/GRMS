from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

GuestCardRequestSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "guest_id": openapi.Schema(type=openapi.TYPE_STRING, description="Guest ID"),
        "cards": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description="List of card numbers (max 10)",
        ),
        "public_spaces": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description="List of public spaces (optional)",
        ),
    },
)

GuestCardResponseSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Success status"),
        "error_rooms": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Error status for rooms"),
        "error_public_spaces": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description="List of public spaces with errors",
        ),
        "msg": openapi.Schema(type=openapi.TYPE_STRING, description="Error message (if any)"),
    },
)

def guest_card_swagger():
    return swagger_auto_schema(
        tags=["Access manager, Guest Card"],
        request_body=GuestCardRequestSwagger,
        responses={200: GuestCardResponseSwagger},
        operation_description="""
        Assign RFID cards to a guest with access permissions.

        The endpoint creates a guest card configuration with:
        - 24/7 access (00:00 to 23:59)
        - Access on all weekdays
        - Default access group

        **Note:** The operation has a 5-second timeout.
        """,
    ) 