from django.http import Http404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import EmailConfiguration
from main.serializers.email_config import EmailConfigSerializer
from main.swagger.email_configuration import (
    EmailConfigSwagger,
    EmailConfigUpdateSwagger,
)


class EmailConfigDetailView(APIView):
    @swagger_auto_schema(responses=EmailConfigSwagger)
    def get(self, request):
        instance = EmailConfiguration.objects.filter(tenant=request.user.tenant).first()
        serializer = EmailConfigSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=EmailConfigSerializer, responses=EmailConfigUpdateSwagger)
    def put(self, request):
        if not request.user.tenant:
            raise Http404("The tenant does not exist in the user!")

        instance = EmailConfiguration.objects.filter(tenant=request.user.tenant).first()
        serializer = EmailConfigSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=request.user.tenant, updated_by=request.user)
        return Response(serializer.data)
