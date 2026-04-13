from access_manager.serializers.card import CardFilterParams, CardSerializer, DisconnectCardSerializer

from drf_yasg.utils import swagger_auto_schema


def card_swagger():
    return swagger_auto_schema(
        query_serializer=CardFilterParams(),
        responses={200: CardSerializer(many=True)},
        tags=["Access manager, Card"],
        operation_description="""
        **This endpoint retrieves a list of `card` objects filtered by the current tenant and the provided query parameters.**

        Represents a named card of access‐card configurations associated with a specific tenant. It includes:

        - Card number and metadata.
        - Link to staff member (if assigned).
        - `need_sync`: shows whether the card is pending synchronization with any device.
        - `staff_id`: filter cards assigned to a specific staff member.
        - `need_sync` (filter): whether the card has any device sync pending.
        """
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
