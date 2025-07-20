from access_manager.serializers.need_sync import SimpleNeedSyncDeviceSerializer

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def sync_device_delete_by_device_swagger():
    return swagger_auto_schema(
        tags=["Access manager, Device Sync By Device"],
        responses={200: openapi.Response(description="Success")},
        operation_description="""
        Delete a specific NeedSyncDevice record by DEVICE_UUID.

        **Parameters:**
        - `device_id` (required): UUID of the Device record to delete.

        **Response codes:**
        """,
    )


def sync_device_delete_swagger():
    return swagger_auto_schema(
        tags=["Access manager, Device Sync"],
        responses={200: openapi.Response(description="Success")},
        operation_description="""
        Delete a specific NeedSyncDevice record by UUID.

        **Parameters:**
        - `id` (required): UUID of the NeedSyncDevice record to delete.

        **Response codes:**
        """,
    )

def sync_device_get_swagger():
    return swagger_auto_schema(
        tags=["Access manager, Device Sync"],
        operation_summary="Get list of devices that need syncing",
        operation_description="""
        Retrieve a list of devices that require synchronization.

        This endpoint filters `NeedSyncDevice` objects by `card_id`. If there are matching records,
        it returns detailed information about each device that is pending synchronization.

        **Query Parameters:**
        - `card_id` (UUID, required): Filter devices by card ID. Only devices linked to this card will be returned.

        **Response:**
        - `200 OK`: Returns a list of devices that need synchronization.
        - `404 Not Found`: No devices found needing synchronization.

        **Response Format:**
        Each device includes details such as:
        - Device info (ID, name, timestamps)
        - Card info
        - Related staff/guest name (if available)
        """,
        manual_parameters=[
            openapi.Parameter(
                name="card_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
                description="Filter devices by Card UUID",
            )
        ],
        responses={
            200: openapi.Response(
                description="List of devices pending synchronization",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "created_by_id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "updated_by": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                            "need_sync": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "device": openapi.Schema(type=openapi.TYPE_OBJECT),  # For brevity
                            "card": openapi.Schema(type=openapi.TYPE_OBJECT),    # For brevity
                            "staff_name": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                            "guest_name": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        }
                    )
                )
            ),
            404: openapi.Response(
                description="No devices found needing synchronization",
            ),
        },
    )


SyncDeviceRequestSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "ids": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID, description="NeedSyncDevice UUID"
            ),
            description="List of NeedSyncDevice UUIDs to sync. If not provided, all devices needing sync will be processed.",
        ),
        "device_ids": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID, description="Device UUID"),
            description="List of Device UUIDs to sync. If provided, all NeedSyncDevice objects for these devices will be processed.",
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

def sync_device_get_swagger():
    return swagger_auto_schema(
        tags=["Access manager, Device Sync"],
        operation_summary="Get list of devices that need syncing",
        operation_description="""
        Retrieve a list of devices that require synchronization.

        This endpoint filters `NeedSyncDevice` objects by `card_id`. If there are matching records,
        it returns detailed information about each device that is pending synchronization.

        **Query Parameters:**
        - `card_id` (UUID, required): Filter devices by card ID. Only devices linked to this card will be returned.

        **Response:**
        - `200 OK`: Returns a list of devices that need synchronization.
        - `404 Not Found`: No devices found needing synchronization.

        **Response Format:**
        Each device includes details such as:
        - Device info (ID, name, timestamps)
        - Card info
        - Related staff/guest name (if available)
        """,
        manual_parameters=[
            openapi.Parameter(
                name="card_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
                description="Filter devices by Card UUID",
            )
        ],
        responses={
            200: openapi.Response(
                description="List of devices pending synchronization",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "created_by_id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "updated_by": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                            "need_sync": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "device": openapi.Schema(type=openapi.TYPE_OBJECT),  # For brevity
                            "card": openapi.Schema(type=openapi.TYPE_OBJECT),    # For brevity
                            "staff_name": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                            "guest_name": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        }
                    )
                )
            ),
            404: openapi.Response(
                description="No devices found needing synchronization",
            ),
        },
    )



def sync_device_swagger():
    return swagger_auto_schema(
        tags=["Access manager, Device Sync"],
        request_body=SyncDeviceRequestSwagger,
        responses={
            200: openapi.Response(description="No devices need syncing", schema=SyncDeviceResponseSwagger),
            202: openapi.Response(
                description="Device sync task started successfully", schema=SyncDeviceResponseSwagger
            ),
            400: openapi.Response(description="Invalid request data", schema=SyncDeviceErrorResponseSwagger),
        },
        operation_description="""
        Synchronize devices that have pending sync operations.
        
        This endpoint processes devices that need synchronization by:
        - Checking for NeedSyncDevice records with failed requests
        - Retrying failed RPC requests for card operations in batches of 10
        - Processing devices in parallel but batches sequentially per device
        - Updating sync status based on operation results
        
        The sync operation runs as a background Celery task with automatic retries.
        
        **Parameters:**
        - `ids` (optional): List of specific NeedSyncDevice UUIDs to sync
        - `device_ids` (optional): List of specific Device UUIDs to sync all their NeedSyncDevice records
        
        **Note:** If both `ids` and `device_ids` are provided, only `ids` will be used.
        If neither is provided, all devices needing sync will be processed.
        
        **Response codes:**
        - `200`: No devices need syncing
        - `202`: Sync task started successfully (async operation)
        - `400`: Invalid request data
        """,
    )
