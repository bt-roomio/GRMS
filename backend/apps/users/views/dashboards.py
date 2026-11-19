from django.db import transaction
from django.db.models import F, OuterRef, Q, Subquery

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from main.models import Dashboard
from main.serializers.dashboard import MyDashboardSerializer, SimpleDashboardSerializer
from users.models import DashboardPosition, User
from users.serializers.dashboard import DashboardOrderSerializer
from users.swagger.dashboards import MyDashboardDetailSwagger, MyDashboardsSwagger


def my_dashboards(user):
    """Dashboards the user gets directly or through a role, in the user's own order."""
    position = DashboardPosition.objects.filter(user=user, dashboard=OuterRef("pk")).values("position")[:1]
    return (
        Dashboard.objects.filter(Q(users=user) | Q(roles__user=user), tenant_id=user.tenant_id)
        .distinct()
        .annotate(position=Subquery(position))
        .order_by(F("position").asc(nulls_last=True), "title")
    )


class MyDashboardsView(APIView):
    @swagger_auto_schema(tags=["Users, My dashboards"], responses=MyDashboardsSwagger)
    def get(self, request):
        return Response(SimpleDashboardSerializer(my_dashboards(request.user), many=True).data)


class MyDashboardDetailView(APIView):
    @swagger_auto_schema(tags=["Users, My dashboards"], responses=MyDashboardDetailSwagger)
    def get(self, request, pk):
        # Looked up only among the caller's own dashboards, so anything else is a plain 404.
        instance = get_object_or_404(my_dashboards(request.user), pk=pk)
        return Response(MyDashboardSerializer(instance).data)


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
