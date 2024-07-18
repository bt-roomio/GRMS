from core.utils.pagination import pagination
from core.utils.permission import IsTenantAndSysAdmin, check_for_tenant
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import User
from users.serializers.user import UserParams, UserSerializer
from users.swagger.users import UserDetailSwagger, UserSwagger


def excluded_fields(user: User):
    fields = user.additional_info and user.additional_info.get("excluded_fields")
    if isinstance(fields, list):
        return fields
    return []


class UserListView(APIView):
    @swagger_auto_schema(responses=UserSwagger, query_serializer=UserParams)
    @check_for_tenant
    def get(self, request):
        params = UserParams.check(request.GET)
        queryset = User.objects.list(
            tenant_id=request.user.tenant_id,
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )
        serializer = UserSerializer(queryset, many=True, context={"excluded_fields": excluded_fields(request.user)})
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    @swagger_auto_schema(responses=UserSwagger, request_body=UserSerializer)
    @check_for_tenant
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data)


class UserDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsTenantAndSysAdmin()]
        return [IsAuthenticated()]

    @swagger_auto_schema(responses=UserDetailSwagger)
    @check_for_tenant
    def get(self, request, pk):
        if "SYS_ADMIN" in [request.user.groups.all()]:
            instance = get_object_or_404(User, id=pk)
        else:
            instance = get_object_or_404(User, id=pk, tenant_id=request.user.tenant_id)
        serializer = UserSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(responses=UserDetailSwagger, request_body=UserSerializer)
    @check_for_tenant
    def put(self, request, pk):
        if "SYS_ADMIN" in [request.user.groups.all()]:
            instance = get_object_or_404(User, id=pk)
        else:
            instance = get_object_or_404(User, id=pk, tenant_id=request.user.tenant_id)
        serializer = UserSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    @check_for_tenant
    def delete(self, request, pk):
        if "SYS_ADMIN" in [request.user.groups.all()]:
            instance = get_object_or_404(User, id=pk)
        else:
            instance = get_object_or_404(User, id=pk, tenant_id=request.user.tenant_id)
        instance.delete()
        return Response({"message": "User deleted"}, 204)
