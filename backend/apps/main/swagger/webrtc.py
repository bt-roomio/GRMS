from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from main.serializers.webrtc import WebrtcBrokerSerializer


def swagger_webrtc_broker():
    return swagger_auto_schema(
        request_body=WebrtcBrokerSerializer(),
        responses={
            200: openapi.Response(
                description="Returns a ticketized proxy URL to open via the WebRTC broker.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "url": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format="uri",
                            example="https://webrtc.example.com/proxy/9b2fb4f3-9a6e-47b2-8e8b-8a6f8e2f2a77/?t=abc123",
                        ),
                    },
                    required=["success", "url"],
                ),
            ),
            400: openapi.Response(description="Validation error (missing/invalid fields)"),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Agent (gateway) offline"),
            502: openapi.Response(description="Broker unreachable"),
            500: openapi.Response(
                description="Unexpected broker error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                        "error": openapi.Schema(type=openapi.TYPE_STRING, example="Agent offline or invalid input"),
                        "details": openapi.Schema(type=openapi.TYPE_OBJECT),
                    },
                    required=["success", "error"],
                ),
            ),
        },
        tags=["WebRTC"],
        operation_description="""
        Accepts a ThingsBoard **gateway UUID** and a target **IP/host** (optionally with `:port`).
        If the gateway (agent) is online, returns a **ticketized** proxy URL that does not reveal the LAN IP.

        ### Request Body
        - `gateway_id` *(UUID, required)* — the gateway's UUID (used as `agent_id`).
        - `ip` *(string, required)* — IP or host (optionally `:port`). The broker will normalize to `http://<ip>`.

        ### Example
        ```json
        {
          "gateway_id": "9b2fb4f3-9a6e-47b2-8e8b-8a6f8e2f2a77",
          "ip": "192.168.1.1"
        }
        ```

        ### Success Response
        - **200** with:
        ```json
        {
          "success": true,
          "url": "https://webrtc.example.com/proxy/9b2f.../?t=abc123"
        }
        ```

        The URL is single-use (or short-lived) and sets the upstream mapping server-side for subsequent navigation.
        """
    )



def swagger_webrtc_agents_status():
    return swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Statuses for the requested gateways.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "results": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            additional_properties=openapi.Schema(type=openapi.TYPE_STRING, enum=["online", "connecting", "offline"]),
                            example={
                                "9b2fb4f3-9a6e-47b2-8e8b-8a6f8e2f2a77": "online",
                                "8d1a0e2f-3c44-4b3d-a9e0-d7d2f8f1c111": "offline",
                            },
                        ),
                    },
                    required=["success", "results"],
                ),
            ),
            400: openapi.Response(description="Validation error"),
            401: openapi.Response(description="Unauthorized"),
            502: openapi.Response(description="Broker unreachable"),
            500: openapi.Response(description="Unexpected broker error"),
        },
        tags=["WebRTC"],
        operation_description="""
        Returns **online/connecting/offline** status for each provided gateway UUID.

        ### Request Body
        - `gateway_ids` *(array of UUIDs, required)*

        ### Example
        ```json
        {
          "gateway_ids": [
            "9b2fb4f3-9a6e-47b2-8e8b-8a6f8e2f2a77",
            "8d1a0e2f-3c44-4b3d-a9e0-d7d2f8f1c111"
          ]
        }
        ```
        """
    )