from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from main.serializers.guest import GuestCheckoutParams, GuestSerializer

GuestSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=GuestSerializer,
    ),
}

GuestDetailSwagger = {200: GuestSerializer}


def swagger_guest_checkout():
    return swagger_auto_schema(
        tags=["Main, Checkout"],
        query_serializer=GuestCheckoutParams(),
        responses={200: '{"message": "{Count} guests have left."}'},
    )
