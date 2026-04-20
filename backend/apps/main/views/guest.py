import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from main.models import Guest, Room
from main.serializers.guest import GuestCheckoutParams, GuestFilterParams, GuestSerializer
from main.swagger.guest import GuestDetailSwagger, GuestSwagger, swagger_guest_checkout

logger = logging.getLogger(__name__)


class GuestListView(APIView):
    @swagger_auto_schema(tags=["Main, Guest"], responses=GuestSwagger, query_serializer=GuestFilterParams())
    @check_perms(["main.view_guest"])
    def get(self, request):
        params = GuestFilterParams.check(request.GET)
        queryset = Guest.objects.list(
            tenant_id=request.user.tenant_id,
            room=params.get("room"),
            sort_by=params.get("sort_by"),
        )
        serializer = GuestSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
        return Response(data)

    @swagger_auto_schema(tags=["Main, Guest"], responses=GuestSwagger, request_body=GuestSerializer)
    @check_perms(["main.add_guest"])
    def post(self, request):
        serializer = GuestSerializer(data=request.data, context={"tenant_id": request.user.tenant_id})
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data, 201)


class GuestDetailView(APIView):
    @swagger_auto_schema(tags=["Main, Guest"], responses=GuestDetailSwagger)
    @check_perms(["main.view_guest"])
    def get(self, request, pk):
        instance = get_object_or_404(Guest, pk=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = GuestSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Main, Guest"], responses=GuestDetailSwagger, request_body=GuestSerializer)
    @check_perms(["main.change_guest"])
    def put(self, request, pk):
        instance = get_object_or_404(Guest, pk=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = GuestSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"tenant_id": request.user.tenant_id},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        deactivate_result = getattr(serializer, "_deactivate_result", None)

        if deactivate_result and not deactivate_result.get("success", True):
            return Response({"message": "Guest successfully checked out."}, status=400)

        return Response(serializer.data)


class GuestCheckoutView(APIView):
    @swagger_guest_checkout()
    def post(self, request):
        params = GuestCheckoutParams.check(request.GET)
        user = str(request.user.id)
        guests, result = Room.objects.guest_checkout(params.get("room").id, user=user)

        if isinstance(result, dict) and not result.get("success", True):
            return Response({"message": f"{guests} guests have left."}, status=400)
        return Response({"message": f"{guests} guests have left."}, status=200)
