import os
import requests

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from main.serializers.webrtc import WebrtcBrokerSerializer

BROKER_BASE_URL = getattr(settings, "WEBRTC_BROKER_URL", os.getenv("WEBRTC_BROKER_URL", "http://localhost:8080"))

class WebrtcBroker(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = WebrtcBrokerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        try:
            r = requests.post(
                f"{BROKER_BASE_URL.rstrip('/')}/api/open",
                json={"agent_id": v["agent_id"], "ip": v["ip"]},
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
                "error": payload.get("error") or "Agent offline or invalid input",
                "details": payload,
            },
            status=500,
        )