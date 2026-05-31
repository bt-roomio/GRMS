from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from access_manager.serializers.card_log import CardLogFilterParams


def swagger_export_card_logs():
    return swagger_auto_schema(
        request_body=CardLogFilterParams(),
        responses={
            200: openapi.Response(
                description="Excel file containing card logs. The response is a downloadable `.xlsx` file."
            ),
            404: openapi.Response(description="No logs found for given filters."),
        },
        tags=["Access manager, CardLogs"],
        operation_description="""
        **This endpoint exports `card log` records into an Excel (`.xlsx`) file.**

        The response is a downloadable Excel file containing all filtered card logs.

        ### Excel File Format:
        The exported file will contain the following columns:
        - **Card Number**
        - **Event Timestamp**
        - **Access Group**
        - **Device**
        - **Spaces**  (line of names of spaces like Room 123, Restaurant)
        - **User Type** (Staff / Guest)
        - **User Name**
        - **Created At**

        ### Filtering Options:
        You can filter the logs by sending JSON in the request body:

        - `room_ids` (array of strings): List of Room IDs
        - `public_space_ids` (array of strings): List of Public Space IDs
        - `user` (string): User ID (staff or guest)
        - `card_num` (string): Card number to filter by
        - `device_ids` (array of strings): Filter by device IDs
        - `filters` (object): Key-value pairs with datetime filtering
          - `from_date` (string, format `"YYYY-MM-DD HH:MM:SS"`)
          - `to_date` (string, format `"YYYY-MM-DD HH:MM:SS"`)
        - `sort_by` (array of strings): Sorting options, e.g. `["-event_ts"]`
        - `size` (integer): Page size, default 50, max 200
        - `page` (integer): Page number, default 1

        ### Example Request Body:
        ```json
        {
          "room_ids": ["uuid-room-1", "uuid-room-2"],
          "public_space_ids": ["uuid-ps-1"],
          "user": "uuid-user",
          "card_num": "98 76 54 32",
          "device_ids": ["dev_1", "dev_2"],
          "filters": {
            "from_date": "2025-07-21 10:00:00",
            "to_date": "2025-07-25 23:59:59"
          },
          "sort_by": ["-event_ts"],
          "size": 100,
          "page": 1
        }
        ```

        ### Responses:
        - **200**: Returns Excel file with logs.
        - **404**: No logs found for given filters.
        """,
    )
