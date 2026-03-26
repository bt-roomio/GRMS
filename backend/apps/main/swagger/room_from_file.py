from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from main.serializers.room_from_file import RoomExportSerializer, RoomFromFileSerializer


def swagger_room_from_file_import():
    return swagger_auto_schema(
        request_body=RoomFromFileSerializer(),
        responses={
            200: openapi.Response(
                description="Import completed successfully. All rooms created/updated atomically.",
                examples={
                    "application/json": {
                        "message": "Import completed: 5 created, 2 updated, 3 skipped.",
                    }
                },
            ),
            400: openapi.Response(
                description="Validation failed. Nothing is created. Returns a single error message.",
                examples={
                    "application/json": {
                        "detail": "Device errors for: 75:7F:44:2C:80:C4, AB:CD:EF:12:34:56."
                        " Please check MAC addresses before importing."
                    }
                },
            ),
        },
        tags=["Main, Room From File"],
        operation_description="""
**Import rooms from a JSON or Excel file.**

Accepts `.json` or `.xlsx` files containing room data with device assignments.

### Required Columns:
- **number** — Room number
- **floor** — Floor identifier
- **block** — Block identifier
- **devices** — Device MAC address(es). JSON: array of strings. Excel: comma-separated string.

### Optional Columns:
- **type** — Room type (e.g. "Standard", "Deluxe"). Created automatically if it doesn't exist.
- **label** — Room label
- **building** — Building name
- **pan_id** — PAN identifier
- **door_lock_device** — Door lock device MAC address
- **public_area_id** — Public area ID (integer)

### Validation Rules:
- All devices must exist, be active, and not be assigned to another room.
- Door lock device must exist, be active, and not be used as door lock by another room.
- Each device MAC address must appear only once across the entire file.
- If any device validation fails for a row, the room is **not** created.
- If a room already exists with identical devices, it is **skipped**.
- If a room already exists with different devices, old devices are unassigned and new ones are assigned.

### JSON File Format:
```json
[
  {
    "number": "101",
    "floor": "1",
    "block": "A",
    "type": "Standard",
    "devices": ["75:7F:44:2C:80:C4"],
    "door_lock_device": "2D:FA:66:D7:6E:BF"
  }
]
```

### Excel File Format:
| Number | Floor | Block | Type     | Devices            | Door Lock Device   |
|--------|-------|-------|----------|--------------------|--------------------|
| 101    | 1     | A     | Standard | 75:7F:44:2C:80:C4  | 2D:FA:66:D7:6E:BF  |

### Responses:
- **200**: Import completed with summary of created, updated, skipped rooms and any errors.
- **400**: File validation failed.
        """,
    )


def swagger_room_export():
    return swagger_auto_schema(
        request_body=RoomExportSerializer(),
        responses={
            200: openapi.Response(
                description="Downloadable file containing room data. "
                "Format depends on the `format` parameter: `.json` or `.xlsx`."
            ),
            400: openapi.Response(description="Validation error (invalid room IDs, unsupported format, etc.)"),
        },
        tags=["Main, Room Export"],
        operation_description="""
**Export rooms to a JSON or Excel file.**

Returns a downloadable file containing room data for the specified rooms,
or all rooms of the tenant if no room IDs are provided.

### Request Body:
- **room_ids** (array of UUIDs, optional) — List of room IDs to export. If empty or omitted, all tenant rooms are exported.
- **format** (string, required) — Export format: `"json"` or `"xlsx"`.

### Example Request Body:
```json
{
  "room_ids": ["uuid-1", "uuid-2"],
  "format": "xlsx"
}
```

Export all rooms:
```json
{
  "format": "json"
}
```

### Exported Columns:
- **Number** — Room number
- **Floor** — Floor identifier
- **Block** — Block identifier
- **Type** — Room type name
- **Devices** — Assigned device MAC addresses
- **Door Lock Device** — Door lock device MAC address

### Responses:
- **200**: Returns downloadable `.json` or `.xlsx` file.
- **400**: Validation error.
        """,
    )
