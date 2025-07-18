import logging
import random

from access_manager.models import Card
from access_manager.serializers.card import CardFilterParams, CardSerializer, DisconnectCardSerializer
from access_manager.swagger.card import card_swagger, swagger_card_disconnect

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from access_manager.utilits.unplug_card import unplug
from core.utils.pagination import pagination
from core.utils.perform_request import with_tenant
from core.utils.permission import check_perms

logger = logging.getLogger(__name__)


class CardListView(APIView):
    @card_swagger()
    @check_perms(["access_manager.view_card"])
    def get(self, request):
        params = CardFilterParams.check(request.GET)
        queryset = Card.objects.list(  # pyright: ignore
            tenant_id=request.user.tenant_id,
            sort_by=params.get("sort_by", []),  # pyright: ignore
            search_field=params.get("search_field"),  # pyright: ignore
            search_value=params.get("search_value"),  # pyright: ignore
        )
        serializer = CardSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @card_swagger()
    @check_perms(["access_manager.add_card"])
    def post(self, request):
        data = with_tenant(request)
        card_number = random.randint(1, 99999999)
        data["number"] = card_number
        serializer = CardSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, 201)


class CardDetailView(APIView):
    @card_swagger()
    @check_perms(["access_manager.view_card"])
    def get(self, request, pk):
        instance = get_object_or_404(Card, pk=pk, tenant_id=request.user.tenant_id)
        serializer = CardSerializer(instance)
        return Response(serializer.data)

    @card_swagger()
    @check_perms(["access_manager.change_card"])
    def put(self, request, pk):
        data = with_tenant(request)
        instance = get_object_or_404(Card, id=pk, tenant_id=request.user.tenant_id)
        serializer = CardSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @card_swagger()
    @check_perms(["access_manager.delete_card"])
    def delete(self, request, pk):
        instance = get_object_or_404(Card, id=pk, tenant_id=request.user.tenant_id)
        result = unplug(instance)
        if result:
            instance.is_active = False
            instance.save()
            return Response({}, 204)
        return Response({}, 204)


class DisconnectCardView(APIView):
    @swagger_card_disconnect()
    def post(self, request):
        serializer = DisconnectCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        if isinstance(result, dict) and not result.get("success", True):
            return Response(result, status=400)

        return Response({"success": True, "message": "Card is deactivated !"}, status=200)
