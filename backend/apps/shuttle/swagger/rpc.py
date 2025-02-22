from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

RPCSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "device": openapi.Schema(type=openapi.TYPE_STRING, description="Device name"),
        "id": openapi.Schema(type=openapi.TYPE_STRING, description="Message ID"),
        "data": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Response data (optional)",
            properties={"success": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Success")},
        ),
    },
)

RPCRequestSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "device": openapi.Schema(type=openapi.TYPE_STRING, description="Device name"),
        "data": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Response data (optional)",
            properties={
                "id": openapi.Schema(type=openapi.TYPE_STRING, description="ID"),
                "method": openapi.Schema(type=openapi.TYPE_STRING, description="RPC method"),
                "params": openapi.Schema(type=openapi.TYPE_OBJECT, description="RPC params"),
            },
        ),
    },
)


def json_rpc_swagger():
    return swagger_auto_schema(
        tags=["Shuttle, JSON RPC"],
        request_body=RPCRequestSwagger,
        responses={200: RPCSwagger},
        operation_description="""
        Sends the one-way remote-procedure call (RPC) request to device. Sends the one-way remote-procedure call (RPC) request to device. The RPC call is A JSON that contains the method name ('method'), parameters ('params') and multiple optional fields. See example below. We will review the properties of the RPC call one-by-one below:

        ```json
        {
          "method": "setGpio",
          "params": {
            "pin": 7,
            "value": 1
          },
          "persistent": false,
          "timeout": 5000
        }
        ```

        **Server-side RPC structure:**

        The body of the server-side RPC request consists of multiple fields:
        - **method** - mandatory, name of the method to distinguish RPC calls (e.g., "getCurrentTime", "getWeatherForecast"). Value is a string.
        - **params** - mandatory, parameters used for processing the request. The value is a JSON object. Leave an empty JSON `{}` if no parameters are needed.
        - **timeout** - optional, processing timeout in milliseconds. Default is 10000 (10 seconds). Minimum value is 5000 (5 seconds).
        - **expirationTime** - optional, epoch time in milliseconds (UTC timezone). Overrides **timeout** if present.
        - **persistent** - optional, indicates whether the RPC is persistent. Default value is false.
        - **retries** - optional, defines how many times persistent RPC will be re-sent in case of failures.
        - **additionalInfo** - optional, metadata for the persistent RPC that will be added to RPC events.

        **RPC Result:**
        In case of persistent RPC, the result of this call is 'rpcId' UUID. In case of lightweight RPC, the result of this call is either 200 OK if the message was sent to device, or 504 Gateway Timeout if device is offline.

        Available for users with 'TENANT_ADMIN' or 'CUSTOMER_USER' authority.
        """,
    )
