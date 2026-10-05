from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from alarms.serializers.rules import validate_profile_alarms
from alarms.services.preview import preview
from alarms.swagger.alarm import preview_swagger
from core.utils.permission import check_perms
from main.models import DeviceProfile


class DeviceProfileAlarmPreviewView(APIView):
    """
    Dry run of a profile's rules before they are saved.

    Takes the rules in the body when they are being edited, and falls back to
    the ones already stored when the body is empty.
    """

    @preview_swagger()
    @check_perms(["main.view_deviceprofile"])
    def post(self, request, pk):
        profile = get_object_or_404(DeviceProfile, pk=pk, tenant_id=request.user.tenant_id, active=True)

        submitted = request.data.get("alarms") if isinstance(request.data, dict) else None
        if submitted is None:
            submitted = (profile.profile_data or {}).get("alarms") or []

        return Response(preview(profile.id, validate_profile_alarms(submitted)))
