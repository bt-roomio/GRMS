import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from main.models import Guest, Room
from main.serializers.guest import GuestCheckoutParams, GuestFilterParams, GuestSerializer
from main.swagger.guest import GuestDetailSwagger, GuestSwagger, swagger_guest_checkout
from core.utils.permission import check_perms

logger = logging.getLogger(__name__)


class GuestListView(APIView):
    @swagger_auto_schema(tags=["Main, Guest"], responses=GuestSwagger, query_serializer=GuestFilterParams())
    @check_perms(["main.view_guest"])
    def get(self, request):
        params = GuestFilterParams.check(request.GET)
        queryset = Guest.objects.list(tenant_id=request.user.tenant_id, room=params.get("room"))
        serializer = GuestSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
        return Response(data)

    @swagger_auto_schema(tags=["Main, Guest"], responses=GuestSwagger, request_body=GuestSerializer)
    @check_perms(["main.add_guest"])
    def post(self, request):
        serializer = GuestSerializer(data=request.data)
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
        serializer = GuestSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data)


class GuestCheckoutView(APIView):
    @swagger_guest_checkout()
    def post(self, request):
        params = GuestCheckoutParams.check(request.GET)
        guests = Room.objects.guest_checkout(params.get("room").id)
        return Response({"message": f"{guests} guests have left."})
