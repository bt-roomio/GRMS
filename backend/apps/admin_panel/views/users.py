from admin_panel.serializers.users import (
    AdminChangePasswordSerializer,
    AdminTenantUsersFilterParams,
)
from admin_panel.swagger.users import (
    AdminChangePasswordSwagger,
    AdminCreateTenantUserSwagger,
    AdminTenantUserDetailSwagger,
    AdminTenantUsersSwagger,
)
from admin_panel.tasks import send_activation_email
from admin_panel.utils.scope import get_scoped_tenant_or_404, get_scoped_user_or_404

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from users.models import User
from users.serializers.user import UserSerializer
from users.utils.emails import send_reset_link_email


class AdminTenantUsersView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantUsersSwagger,
        query_serializer=AdminTenantUsersFilterParams(),
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns a list of active users for the given tenant.",
    )
    def get(self, request, tenant_id):
        get_scoped_tenant_or_404(request, tenant_id)
        params = AdminTenantUsersFilterParams.check(request.GET)
        queryset = User.objects.list(
            tenant_id=tenant_id,
            sort_by=params.get("sort_by"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
        )
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        request_body=UserSerializer,
        responses=AdminCreateTenantUserSwagger,
        security=[{"Bearer": []}],
        operation_description=(
            "**Superuser only.** Creates a user for the given tenant. "
            "Pass `?send_activation_mail=true` to send activation email, "
            "otherwise the activation link is returned in the response."
        ),
    )
    def post(self, request, tenant_id):
        get_scoped_tenant_or_404(request, tenant_id)
        serializer = UserSerializer(data=request.data, context={"request": request, "tenant_id": tenant_id})
        serializer.is_valid(raise_exception=True)
        user = serializer.save(tenant_id=tenant_id)

        response_data = {"user": serializer.data}
        if request.query_params.get("send_activation_mail", "false").lower() == "true":
            send_activation_email.delay(str(user.id))
            response_data["message"] = "Activation link sent."
        else:
            link = send_reset_link_email(user, send_activation_mail=False)
            response_data["activation_link"] = link.decode("utf-8")

        return Response(response_data, 201)


class AdminTenantUserDetailView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantUserDetailSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns details of a specific user within a tenant.",
    )
    def get(self, request, tenant_id, user_id):
        get_scoped_tenant_or_404(request, tenant_id)
        user = get_object_or_404(User, id=user_id, tenant_id=tenant_id)
        serializer = UserSerializer(user)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        request_body=UserSerializer,
        responses=AdminTenantUserDetailSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Updates a user's data (including roles) within a tenant.",
    )
    def put(self, request, tenant_id, user_id):
        get_scoped_tenant_or_404(request, tenant_id)
        user = get_object_or_404(User, id=user_id, tenant_id=tenant_id)
        serializer = UserSerializer(user, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminChangePasswordView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        request_body=AdminChangePasswordSerializer,
        responses=AdminChangePasswordSwagger,
        security=[{"Bearer": []}],
        operation_description=(
            "**Superuser only.** Directly sets a new password for any account the caller administers: "
            "a user of a hotel in scope, or the admin of a chain in scope. "
            "A superuser without a chain pin cannot be targeted here."
        ),
    )
    def post(self, request, user_id):
        user = get_scoped_user_or_404(request, user_id)
        serializer = AdminChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"message": "Password changed."})
