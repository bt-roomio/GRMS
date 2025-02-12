from access_manager.serializers.group import GroupFilterParams, GroupSerializer
from drf_yasg.utils import swagger_auto_schema


def group_swagger():
    return swagger_auto_schema(
        query_serializer=GroupFilterParams(),
        responses={200: GroupSerializer()},
        tags=["Card"],
        operation_description="""

        **This endpoint retrieves a list of `Group` objects filtered by the current tenant and the provided query parameters.**


        Represents a named group of access‐card configurations associated with a specific tenant. It includes:
            - A name for identification.
            - A link to the tenant it belongs to.
            - A list of weekdays on which this group is active (stored as an array of valid weekday choices).
            - A start time and end time that define the daily time range for activation.
            - An expiry date after which the group is no longer valid.
            - An “is_active” flag or status indicator.

            """,
    )
