from access_manager.serializers.card import CardFilterParams, CardSerializer
from drf_yasg.utils import swagger_auto_schema


def card_swagger():
    return swagger_auto_schema(
        query_serializer=CardFilterParams(),
        responses={200: CardSerializer()},
        tags=["Access manager, Card"],
        operation_description="""

        **This endpoint retrieves a list of `card` objects filtered by the current tenant and the provided query parameters.**


        Represents a named card of access‐card configurations associated with a specific tenant. It includes:
            - A name for identification.
            - A link to the tenant it belongs to.
            - A list of weekdays on which this card is active (stored as an array of valid weekday choices).
            - A start time and end time that define the daily time range for activation.
            - An expiry date after which the card is no longer valid.

            """,
    )
