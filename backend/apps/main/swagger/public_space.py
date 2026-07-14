from drf_yasg.utils import swagger_auto_schema

from main.serializers.public_space import PublicSpaceFilterParams, PublicSpaceSerializer


def public_space_swagger():
    return swagger_auto_schema(
        query_serializer=PublicSpaceFilterParams(),
        responses={200: PublicSpaceSerializer()},
        tags=["Main, PublicSpace"],
        operation_description="""

        **This endpoint retrieves a list of `public_space` objects filtered by the current tenant and the provided query parameters.**


        Represents a named public_space of access‐card configurations associated with a specific tenant. It includes:
            - A name for identification.
            - A link to the tenant it belongs to.
            - A list of weekdays on which this public_space is active (stored as an array of valid weekday choices).
            - A start time and end time that define the daily time range for activation.
            - An expiry date after which the public_space is no longer valid.
            - A `status` flag derived from connected devices: `true` when every linked device is online,
              `false` when any linked device is offline or no devices are linked.

        Query parameters:
            - `status` (optional, `true`/`false`): filter Public Spaces by the aggregated device-online status.
              When omitted, status filtering is not applied.
            - `search_field=device_name` with `search_value`: case-insensitive partial match against the names
              of the devices linked to a Public Space.

            """,
    )
