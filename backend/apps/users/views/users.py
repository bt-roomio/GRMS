from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import User
from users.serializers.user import UserParams, UserSerializer


class UserListView(APIView):
    def get(self, request):
        if not request.user.tenant_id:
            return Response({"error": "You are not allowed to view this page"}, 403)

        users = User.objects.prefetch_related("groups").filter(tenant_id=request.user.tenant_id)
        for user in users:
            print(user.groups.all())
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not request.user.tenant_id:
            return Response({"error": "You are not allowed to view this page"}, 403)
        params = UserParams.check(request.GET)
        serializer = UserSerializer(data=request.data, context={"params": params})
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data)


class UserDetailView(APIView):
    @swagger_auto_schema(
        responses={
            200: UserSerializer(),
            401: "Authentication credentials were not provided.",
        }
    )
    def get(self, request):
        user = get_object_or_404(User, id=request.user.id)
        serializer = UserSerializer(user)
        return Response(serializer.data)
