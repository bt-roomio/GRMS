from drf_yasg import openapi


RoomSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {
            "count": "Count of data.",
            "results": "Array of data."
        }
    }),
}
