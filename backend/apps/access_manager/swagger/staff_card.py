from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

StaffCardRequestSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "staff_id": openapi.Schema(type=openapi.TYPE_STRING, description="Staff ID"),
        "cards": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description="List of card numbers (max 10)",
        ),
    },
)

StaffCardResponseSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Success status"),
        "error_rooms": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Error status for rooms"),
        "msg": openapi.Schema(type=openapi.TYPE_STRING, description="Error message (if any)"),
    },
)


def staff_card_swagger():
    return swagger_auto_schema(
        tags=["Access manager, Staff Card"],
        request_body=StaffCardRequestSwagger,
        responses={200: StaffCardResponseSwagger},
        operation_description="""
        Assign RFID cards to a staff with access permissions.

        The endpoint creates a staff card configuration with:
        - 24/7 access (00:00 to 23:59)
        - Access on all weekdays
        - Default access group

        **Note:** The operation has a 5-second timeout.
        """,
    )
