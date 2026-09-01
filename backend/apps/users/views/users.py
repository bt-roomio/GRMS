from django.contrib.auth.models import Permission
from django.db.models import Prefetch

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from users.models import Role, User
from users.serializers.user import UserDetailSerializer, UserParams, UserSerializer
from users.swagger.users import UserDetailSwagger, UserSwagger
from users.utils.tenant_access import available_tenants_qs, is_unscoped_superuser


def reachable_users(request, queryset=None):
    """
    Narrow a user queryset to what the caller may open by id.

    `is_superuser` alone is not the system-wide tier any more: a chain admin is a
    superuser too, and must stay inside their own chain. For an ordinary user the
    scope collapses to their own hotel, exactly as the old tenant filter did.
    """
    queryset = User.objects.all() if queryset is None else queryset
    if is_unscoped_superuser(request.user):
        return queryset
    return queryset.filter(tenant__in=available_tenants_qs(request.user))


class UserListView(APIView):
    @swagger_auto_schema(tags=["Users, User"], responses=UserSwagger, query_serializer=UserParams)
    @check_perms(["users.view_user"])
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

    @swagger_auto_schema(tags=["Users, User"], responses=UserSwagger, request_body=UserSerializer)
    @check_perms(["users.add_user"])
    def post(self, request):
        serializer = UserSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data, 201)


class UserDetailView(APIView):
    @swagger_auto_schema(tags=["Users, User"], responses=UserDetailSwagger)
    def get(self, request, pk):
        queryset = User.objects.prefetch_related(
            Prefetch("roles", queryset=Role.objects.order_by("name")),
            Prefetch("roles__permissions", queryset=Permission.objects.order_by("-id")),
        )
        instance = get_object_or_404(reachable_users(request, queryset), id=pk, is_active=True)
        serializer = UserDetailSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Users, User"], responses=UserDetailSwagger, request_body=UserSerializer)
    @check_perms(["users.change_user"])
    def put(self, request, pk):
        instance = get_object_or_404(reachable_users(request), id=pk, is_active=True)
        serializer = UserSerializer(instance, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Users, User"], responses={})
    @check_perms(["users.delete_user"])
    def delete(self, request, pk):
        instance = get_object_or_404(User, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        instance.is_active = False
        instance.save()
        return Response({"message": "User deactivated"}, 200)
