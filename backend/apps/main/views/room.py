from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ReturnDict
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from core.utils.serializers import dict_of_lists
from main.models import Room
from main.serializers.room import RoomFilterParams, RoomFilterParamsSwagger, RoomSerializer
from main.serializers.room_bulk_create import RoomNumberValidator
from main.swagger.room import RoomDetailSwagger, RoomSwagger
from main.utils.parse_room_numbers import parse_room_numbers


class RoomListView(APIView):
    @swagger_auto_schema(tags=["Main, Room"], responses=RoomSwagger, query_serializer=RoomFilterParamsSwagger())
    @check_perms(["main.view_room"])
    def get(self, request):
        params = RoomFilterParams.check(request.query_params)
        queryset = Room.objects.list(
            tenant=request.user.tenant,
            state=params.get("state"),
            status=params.get("status"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )
        serializer = RoomSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
        return Response(data)

    @swagger_auto_schema(tags=["Main, Room"], responses=RoomSwagger, request_body=RoomSerializer)
    @check_perms(["main.add_room"])
    def post(self, request):
        tenant_id = request.user.tenant_id
        data = request.data.copy()
        data["tenant"] = tenant_id
        room_number = RoomNumberValidator(data=data)
        room_number.is_valid(raise_exception=True)

        if not isinstance(room_number.data, ReturnDict):
            raise DRFValidationError({"number": "Invalid room number"})

        numbers = parse_room_numbers(room_number.data.get("number", ""))
        existing = set(
            Room.objects.filter(number__in=numbers, tenant_id=tenant_id, active=True).values_list("number", flat=True)
        )
        to_create = [n for n in numbers if n not in existing]

        if not to_create or len(to_create) == 0:
            raise DRFValidationError({"number": "Room number already exists"})

        if len(to_create) > 1:
            with transaction.atomic():
                rooms = []
                for n in to_create:
                    obj = Room.objects.get_or_create(
                        number=n,
                        tenant_id=tenant_id,
                        type_id=data.get("type"),
                        label=data.get("label"),
                        floor=data.get("floor"),
                        block=data.get("block"),
                    )
                    rooms.append(obj[0])
                serializer = RoomSerializer(instance=rooms, many=True)
                return Response(serializer.data, 201)

        data["number"] = to_create[0]
        serializer = RoomSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except DjangoValidationError as e:
            raise DRFValidationError(e.message_dict)
        if not isinstance(serializer.data, ReturnDict):
            raise DRFValidationError({"number": "Invalid room number"})

        return Response(dict_of_lists(serializer.data), 201)


class RoomDetailView(APIView):
    @swagger_auto_schema(tags=["Main, Room"], responses=RoomDetailSwagger)
    @check_perms(["main.view_room"])
    def get(self, request, pk):
        queryset = get_object_or_404(Room, id=pk, active=True, tenant_id=request.user.tenant_id)
        serializer = RoomSerializer(queryset, context={"detail": True})
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Main, Room"], responses=RoomDetailSwagger, request_body=RoomSerializer)
    @check_perms(["main.change_room"])
    def put(self, request, pk):
        instance = get_object_or_404(Room, id=pk, active=True)
        serializer = RoomSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Main, Room"], responses={})
    @check_perms(["main.delete_room"])
    def delete(self, request, pk):
        instance = get_object_or_404(Room, id=pk, tenant_id=request.user.tenant_id)
        instance.delete()
        return Response({}, 204)
