from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from users.models import User
from users.serializers.user import UserParams, UserSerializer, UserDetailSerializer
from users.swagger.users import UserDetailSwagger, UserSwagger


class UserListView(APIView):
    @swagger_auto_schema(responses=UserSwagger, query_serializer=UserParams)
    def get(self, request):
        params = UserParams.check(request.GET)
        queryset = User.objects.list(
            tenant_id=request.user.tenant_id,
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )
        serializer = UserSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    @swagger_auto_schema(responses=UserSwagger, request_body=UserSerializer)
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data)


class UserDetailView(APIView):
    @swagger_auto_schema(responses=UserDetailSwagger)
    def get(self, request, pk):
        queryset = User.objects.prefetch_related("roles", "roles__permissions")
        instance = get_object_or_404(queryset, id=pk, tenant=request.user.tenant_id)
        serializer = UserDetailSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(responses=UserDetailSwagger, request_body=UserSerializer)
    def put(self, request, pk):
        instance = get_object_or_404(User, id=pk, tenant_id=request.user.tenant_id)
        serializer = UserSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    def delete(self, request, pk):
        instance = get_object_or_404(User, id=pk, tenant_id=request.user.tenant_id)
        instance.delete()
        return Response({"message": "User deleted"}, 204)
