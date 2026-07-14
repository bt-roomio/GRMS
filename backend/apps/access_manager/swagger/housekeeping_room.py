from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

HousekeepingRoomRequestSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["room_id", "remove"],
    properties={
        "room_id": openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID,
            description="ID of the room to assign to / remove from the HOUSEKEEPING group.",
        ),
        "remove": openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description=(
                "`True` removes the room from the HOUSEKEEPING group and erases the group's "
                "staff cards from the room's devices. `False` assigns the room to the group and "
                "writes those staff cards back to the room's devices."
            ),
        ),
    },
)


def housekeeping_room_swagger():
    return swagger_auto_schema(
        tags=["Access manager, Group"],
        request_body=HousekeepingRoomRequestSwagger,
        operation_description="""
        Assign a room to or remove it from the tenant's HOUSEKEEPING group.

        Driven by the `remove` flag:
        - `remove=false` → attach the room to the group and connect the group's staff cards
          to the room's devices.
        - `remove=true` → detach the room from the group and disconnect those staff cards
          from the room's devices.

        Card synchronisation is handled asynchronously per device.
        """,
    )
