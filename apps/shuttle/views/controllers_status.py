from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device
from shuttle.swagger.controllers_status import controller_status_swagger


class ControllersStatusView(APIView):
    @controller_status_swagger()
    def get(self, request):
        queryset = Device.objects.filter(tenant=request.user.tenant, room__isnull=False)
        queryset = queryset.values("status")
        queryset = queryset.annotate(count=Count("status"))
        return Response(queryset)
