from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

SyncDeviceRequestSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "ids": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                description="NeedSyncDevice UUID"
            ),
            description="List of NeedSyncDevice UUIDs to sync. If not provided, all devices needing sync will be processed.",
        ),
    },
)

SyncDeviceResponseSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Success status"),
        "message": openapi.Schema(type=openapi.TYPE_STRING, description="Response message"),
    },
)

SyncDeviceErrorResponseSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Success status"),
        "message": openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
        "errors": openapi.Schema(type=openapi.TYPE_OBJECT, description="Validation errors"),
    },
)

def sync_device_swagger():
    return swagger_auto_schema(
        tags=["Access manager, Device Sync"],
        request_body=SyncDeviceRequestSwagger,
        responses={
            200: openapi.Response(
                description="No devices need syncing",
                schema=SyncDeviceResponseSwagger
            ),
            202: openapi.Response(
                description="Device sync task started successfully",
                schema=SyncDeviceResponseSwagger
            ),
            400: openapi.Response(
                description="Invalid request data",
                schema=SyncDeviceErrorResponseSwagger
            ),
        },
        operation_description="""
        Synchronize devices that have pending sync operations.
        
        This endpoint processes devices that need synchronization by:
        - Checking for NeedSyncDevice records with failed requests
        - Retrying failed RPC requests for card operations
        - Updating sync status based on operation results
        
        The sync operation runs as a background Celery task with automatic retries.
        
        **Parameters:**
        - `ids` (optional): List of specific NeedSyncDevice UUIDs to sync. If omitted, all devices needing sync will be processed.
        
        **Response codes:**
        - `200`: No devices need syncing
        - `202`: Sync task started successfully (async operation)
        - `400`: Invalid request data
        """,
    ) 