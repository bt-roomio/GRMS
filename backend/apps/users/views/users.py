from core.utils.permission import IsTenantAndSysAdmin
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import User
from users.serializers.user import UserParams, UserSerializer


class UserListView(APIView):
    def get(self, request):
        if not request.user.tenant_id:
            return Response({"error": "You are not allowed to view this page"}, 403)

        users = User.objects.prefetch_related("groups").filter(tenant_id=request.user.tenant_id)
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
    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsTenantAndSysAdmin()]
        return [IsAuthenticated()]

    def get(self, request, pk):
        if "SYS_ADMIN" in [request.user.groups.all()]:
            instance = get_object_or_404(User, id=pk)
        else:
            instance = get_object_or_404(User, id=pk, tenant_id=request.user.tenant_id)
        serializer = UserSerializer(instance)
        return Response(serializer.data)

    def put(self, request, pk):
        if "SYS_ADMIN" in [request.user.groups.all()]:
            instance = get_object_or_404(User, id=pk)
        else:
            instance = get_object_or_404(User, id=pk, tenant_id=request.user.tenant_id)
        serializer = UserSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        if "SYS_ADMIN" in [request.user.groups.all()]:
            instance = get_object_or_404(User, id=pk)
        else:
            instance = get_object_or_404(User, id=pk, tenant_id=request.user.tenant_id)
        instance.delete()
        return Response({"message": "User deleted"}, 204)
