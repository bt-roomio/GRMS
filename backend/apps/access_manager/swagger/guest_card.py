from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

GuestCardRequestSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "guest_id": openapi.Schema(type=openapi.TYPE_STRING, description="Guest ID"),
        "cards": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description=(
                "List of card numbers (max 10). When `is_pwd=true`, only the first entry is "
                "used (a single PIN per request); any additional entries are silently dropped."
            ),
        ),
        "public_spaces": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description="List of public spaces (optional)",
        ),
        "is_pwd": openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description=(
                "When `true`, the request is for a PIN/password credential. The backend dispatches "
                "`add_pwd` instead of `writeRFID` and accepts only one entry in `cards`. "
                "Defaults to `false` (RFID card)."
            ),
            default=False,
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
        Assign RFID cards or a PIN/password credential to a guest with access permissions.

        The endpoint creates a guest card configuration with:
        - 24/7 access (00:00 to 23:59)
        - Access on all weekdays
        - Default access group

        **PIN credentials (`is_pwd=true`):**
        - Only one PIN can be assigned per request — extra `cards` entries are dropped.
        - The backend dispatches `add_pwd` (numeric PIN payload) instead of `writeRFID`.
        - Disconnect / removal flows automatically dispatch `remove_pwd` for these rows.

        **Note:** The operation has a 5-second timeout.
        """,
    ) 