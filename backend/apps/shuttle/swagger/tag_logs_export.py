from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from shuttle.serializers.ts_kv import TagLogsFilterParams


def swagger_export_tag_logs():
    return swagger_auto_schema(
        request_body=TagLogsFilterParams(),
        responses={
            200: openapi.Response(
                description="Excel file containing tag logs. The response is a downloadable `.xlsx` file."
            ),
            404: openapi.Response(
                description="No tag logs found for given filters."
            ),
        },
        tags=["Shuttle, Tag"],
        operation_description="""
        **This endpoint exports `tag log` records into an Excel (`.xlsx`) file.**

        The response is a downloadable Excel file containing all filtered tag logs.  

        ### Excel File Format:
        The exported file will contain the following columns:
        - **Timestamp**
        - **Key Name**
        - **Value**
        - **Data Type**

        The first row of the file will also include a title with the **device name** and the **spaces** the device is connected to.

        ### Filtering Options:
        You can filter the logs by sending JSON in the request body:

        - `device` (string): Device ID (UUID)  
        - `keys` (list of strings): Filter by key names  
        - `start_ts` (string, datetime): Start timestamp (format: `"YYYY-MM-DD HH:MM:SS"`)  
        - `end_ts` (string, datetime): End timestamp (format: `"YYYY-MM-DD HH:MM:SS"`)  
        - `sort_by` (list): Sorting options, e.g. `["-ts"]`  

        ### Example Request Body:
        ```json
        {
          "device": "uuid",
          "keys": ["temperature", "humidity"],
          "start_ts": "2025-07-21 10:00:00",
          "end_ts": "2025-07-25 23:59:59",
          "sort_by": ["-ts"]
        }
        ```

        ### Responses:
        - **200**: Returns Excel file with tag logs.  
        - **404**: No tag logs found for given filters.  
        """
    )
