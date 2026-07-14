from drf_yasg.utils import swagger_auto_schema

from access_manager.serializers.staff import StaffFilterParams, StaffSerializer


def staff_swagger():
    return swagger_auto_schema(
        query_serializer=StaffFilterParams(),
        responses={200: StaffSerializer()},
        tags=["Access manager, Staff"],
        operation_description="""

        **This endpoint retrieves a list of `staff` objects filtered by the current tenant and the provided query parameters.**


        Represents a named staff of access‐card configurations associated with a specific tenant. It includes:
            - A name for identification.
            - A link to the tenant it belongs to.
            - A list of weekdays on which this staff is active (stored as an array of valid weekday choices).
            - A start time and end time that define the daily time range for activation.
            - An expiry date after which the staff is no longer valid.
            - An “is_active” flag or status indicator.

            """,
    )
