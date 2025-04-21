from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from shuttle.models import Relation
from shuttle.serializers.relation import RelationFilterParams, RelationSerializer
from shuttle.swagger.relation import relation_swagger


class RelationListView(APIView):
    @relation_swagger(query_serializer=RelationFilterParams())
    @check_perms(["shuttle.view_relation"])
    def get(self, request):
        params = RelationFilterParams.check(request.GET)
        queryset = Relation.objects.list(  # pyright: ignore
            tenant=request.user.tenant,
            from_id=params.get("from_id"),  # pyright: ignore
            to_id=params.get("to_id"),  # pyright: ignore
        )
        serializer = RelationSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))  # pyright: ignore
        return Response(data)

    @relation_swagger(request_body=RelationSerializer)
    @check_perms(["shuttle.add_relation"])
    def post(self, request):
        serializer = RelationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RelationDetailView(APIView):
    @relation_swagger(request_body=RelationSerializer)
    @check_perms(["shuttle.change_relation"])
    def put(self, request, pk):
        instance = get_object_or_404(Relation, pk=pk, from_id__tenant=request.user.tenant, from_id__is_active=True)
        serializer = RelationSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={204: ""}, tags=["Shuttle, Relation"])
    @check_perms(["shuttle.delete_relation"])
    def delete(self, request, pk):
        instance = get_object_or_404(Relation, pk=pk, from_id__tenant=request.user.tenant, from_id__is_active=True)
        instance.delete()
        return Response({}, 204)
