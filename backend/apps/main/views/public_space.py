from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.perform_request import with_tenant
from main.models import PublicSpace
from main.serializers.public_space import PublicSpaceFilterParams, PublicSpaceSerializer
from main.swagger.public_space import public_space_swagger


class PublicSpaceListView(APIView):
    @public_space_swagger()
    def get(self, request):
        params = PublicSpaceFilterParams.check(request.GET)
        queryset = PublicSpace.objects.list(  # pyright: ignore
            tenant_id=request.user.tenant_id,
            sort_by=params.get("sort_by", []),  # pyright: ignore
            search_field=params.get("search_field"),  # pyright: ignore
            search_value=params.get("search_value"),  # pyright: ignore
        )
        serializer = PublicSpaceSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @public_space_swagger()
    def post(self, request):
        data = with_tenant(request)
        serializer = PublicSpaceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, 201)


class PublicSpaceDetailView(APIView):
    @public_space_swagger()
    def get(self, request, pk):
        instance = get_object_or_404(PublicSpace, pk=pk, tenant_id=request.user.tenant_id)
        serializer = PublicSpaceSerializer(instance)
        return Response(serializer.data)

    @public_space_swagger()
    def put(self, request, pk):
        data = with_tenant(request)
        instance = get_object_or_404(PublicSpace, id=pk, tenant_id=request.user.tenant_id)
        serializer = PublicSpaceSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @public_space_swagger()
    def delete(self, request, pk):
        instance = get_object_or_404(PublicSpace, id=pk, tenant_id=request.user.tenant_id)
        instance.delete()
        return Response({}, 204)
