from access_manager.serializers.card import CardFilterParams, CardSerializer, DisconnectCardSerializer
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


def swagger_card_disconnect():
    return swagger_auto_schema(
        request_body=DisconnectCardSerializer(),
        responses={200: DisconnectCardSerializer()},
        tags=["Access manager, Card"],
        operation_description="""
        
        **This endpoint deactivates an active guest card in the system with the provided card_id.**
        
        The card disconnection process:
            - Finds the active guest card with the specified card_id
            - Sends a deactivation request to the associated device
            - Marks the card as inactive in the system
            
        """,
    )
