from drf_yasg.utils import swagger_auto_schema

from shuttle.serializers.remove_attribute import RemoveAttributeFilterParams


def remove_attribute_swagger():
    return swagger_auto_schema(
        tags=["Shuttle, Remove attribute"],
        query_serializer=RemoveAttributeFilterParams(),
        responses={
            200: '{"message": "Removed [keys]}',
            404: '{"detail": "Not found these keys!"}',
        },
        operation_description="""
        Delete device attributes using provided Device Id, scope and a list of keys. Referencing a non-existing Device Id will cause an error

        Available for users with 'TENANT_ADMIN' or 'CUSTOMER_USER' authority.
        """,
    )
