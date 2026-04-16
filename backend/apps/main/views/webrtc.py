import os

import requests
from django.conf import settings

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device
from main.serializers.webrtc import WebrtcBrokerSerializer
from main.swagger.webrtc import swagger_webrtc_agents_status, swagger_webrtc_broker

BROKER_BASE_URL = getattr(settings, "WEBRTC_BROKER_URL", os.getenv("WEBRTC_BROKER_URL", "http://localhost:8080"))

class WebrtcBroker(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_webrtc_broker()
    def post(self, request):
        ser = WebrtcBrokerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        payload = {"agent_id": v["gateway_id"], "ip": v["ip"]}
        try:
            r = requests.post(
                f"{BROKER_BASE_URL.rstrip('/')}/api/open",
                json=payload,
                timeout=7,
            )
        except requests.RequestException as e:
            return Response({"success": False, "error": f"Broker unreachable: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        try:
            payload = r.json()
        except ValueError:
            payload = {"ok": False, "error": f"Non-JSON from broker (HTTP {r.status_code})"}

        if r.status_code == 200 and payload.get("success"):
            return Response({"success": True, "url": payload.get("url")}, status=200)

        return Response(
            {
                "success": False,
                "error": payload.get("message") or "Agent offline or invalid input",
                "details": payload,
            },
            status=500,
        )


class WebrtcAgentStatus(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_webrtc_agents_status()
    def get(self, request):
        tenant = self.request.user.tenant
        qs = Device.objects.filter(tenant=tenant, is_active=True, additional_info__gateway=True).only("id")
        gateway_ids = [str(d.id) for d in qs]
        if not gateway_ids:
            return Response({"success": True, "results": {}, "count": 0}, status=200)
        try:
            r = requests.post(
                f"{BROKER_BASE_URL.rstrip('/')}/api/agents/status",
                json={"gateway_ids": gateway_ids}, timeout=7)
        except requests.RequestException as e:
            return Response({"success": False, "error": f"Broker unreachable: {e}"}, status=500)

        try:
            payload = r.json()
        except ValueError:
            payload = {"success": False, "message": f"Non-JSON from broker (HTTP {r.status_code})"}

        if r.status_code == 200 and payload.get("success") is True:
            results = payload.get("results") or {}
            normalized = {gid: results.get(gid, "offline") for gid in gateway_ids}
            return Response({"success": True, "results": normalized, "count": len(normalized)}, status=200)

        return Response({"success": False, "error": payload.get("message") or payload.get("error") or "Broker error",
                         "details": payload}, status=502)
