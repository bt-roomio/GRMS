from django.db import transaction
from django.db.models import F, OuterRef, Q, Subquery

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from main.models import Dashboard
from main.serializers.dashboard import DashboardFilterParams, SimpleDashboardSerializer
from main.views.dashboard import ensure_not_linked_to_room_types
from users.models import DashboardPosition, User
from users.serializers.dashboard import DashboardOrderSerializer, UserDashboardSerializer
from users.swagger.dashboards import MyDashboardsSwagger, UserDashboardDetailSwagger, UserDashboardSwagger


def user_dashboards(request):
    """Dashboards of the caller's hotel that are assigned to a user or a role."""
    return Dashboard.objects.filter(tenant_id=request.user.tenant_id).assigned()


def my_dashboards(user):
    """Dashboards the user gets directly or through a role, in the user's own order."""
    position = DashboardPosition.objects.filter(user=user, dashboard=OuterRef("pk")).values("position")[:1]
    return (
        Dashboard.objects.filter(Q(users=user) | Q(roles__user=user), tenant_id=user.tenant_id)
        .distinct()
        .annotate(position=Subquery(position))
        .order_by(F("position").asc(nulls_last=True), "title")
    )


class UserDashboardListView(APIView):
    @swagger_auto_schema(
        tags=["Users, Dashboard"], responses=UserDashboardSwagger, query_serializer=DashboardFilterParams()
    )
    @check_perms(["main.view_dashboard"])
    def get(self, request):
        params = DashboardFilterParams.check(request.GET)
        queryset = Dashboard.objects.list(
            tenant_id=request.user.tenant_id,
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by", []),
        )
        queryset = queryset.assigned().prefetch_related("users", "roles")
        serializer = UserDashboardSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    @swagger_auto_schema(
        tags=["Users, Dashboard"], responses=UserDashboardDetailSwagger, request_body=UserDashboardSerializer
    )
    @check_perms(["main.add_dashboard"])
    def post(self, request):
        serializer = UserDashboardSerializer(data=request.data, context={"tenant_id": request.user.tenant_id})
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data, 201)


class UserDashboardDetailView(APIView):
    @swagger_auto_schema(tags=["Users, Dashboard"], responses=UserDashboardDetailSwagger)
    @check_perms(["main.view_dashboard"])
    def get(self, request, pk):
        instance = get_object_or_404(user_dashboards(request).prefetch_related("users", "roles"), pk=pk)
        return Response(UserDashboardSerializer(instance).data)

    @swagger_auto_schema(
        tags=["Users, Dashboard"], responses=UserDashboardDetailSwagger, request_body=UserDashboardSerializer
    )
    @check_perms(["main.change_dashboard"])
    def put(self, request, pk):
        # No prefetch: holders change during save and the response must show the new set.
        instance = get_object_or_404(user_dashboards(request), pk=pk)
        serializer = UserDashboardSerializer(instance, data=request.data, context={"tenant_id": request.user.tenant_id})
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Users, Dashboard"], responses={})
    @check_perms(["main.delete_dashboard"])
    def delete(self, request, pk):
        instance = get_object_or_404(user_dashboards(request), pk=pk)
        ensure_not_linked_to_room_types(instance)
        # Its user/role links and everyone's positions go with it.
        instance.delete()
        return Response({}, 204)


class MyDashboardsView(APIView):
    @swagger_auto_schema(tags=["Users, My dashboards"], responses=MyDashboardsSwagger)
    def get(self, request):
        return Response(SimpleDashboardSerializer(my_dashboards(request.user), many=True).data)


class MyDashboardsOrderView(APIView):
    @swagger_auto_schema(
        tags=["Users, My dashboards"], responses=MyDashboardsSwagger, request_body=DashboardOrderSerializer
    )
    def put(self, request):
        available = my_dashboards(request.user)
        ids = DashboardOrderSerializer.check(request.data, context={"available": available})["ids"]
        with transaction.atomic():
            # Serialise concurrent saves of the same user (double click, two tabs): otherwise both
            # delete, both insert and the second trips the unique (user, dashboard) constraint.
            User.objects.select_for_update().filter(pk=request.user.pk).first()
            # Rows of dashboards the user no longer has go too, so the table does not keep stale entries.
            request.user.dashboard_positions.all().delete()
            DashboardPosition.objects.bulk_create(
                DashboardPosition(user=request.user, dashboard_id=pk, position=index) for index, pk in enumerate(ids)
            )
        return Response(SimpleDashboardSerializer(my_dashboards(request.user), many=True).data)
