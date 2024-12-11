from core.utils.pagination import pagination
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from shuttle.models import Relation
from shuttle.serializers.relation import RelationFilterParams, RelationSerializer


class RelationListView(APIView):
    def get(self, request):
        params = RelationFilterParams.check(request.GET)
        queryset = Relation.objects.select_related("from_id").filter(from_id__tenant=request.user.tenant)
        serializer = RelationSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
        return Response(data)

    def post(self, request):
        serializer = RelationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RelationDetailView(APIView):
    def put(self, request, pk):
        instance = get_object_or_404(Relation, pk=pk, from_id__tenant=request.user.tenant)
        serializer = RelationSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        instance = get_object_or_404(Relation, pk=pk, from_id__tenant=request.user.tenant)
        instance.delete()
        return Response({}, 204)
