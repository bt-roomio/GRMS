import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from alarms.whatsapp.phone import mask_phone

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "HTTP_X_HUB_SIGNATURE_256"
SIGNATURE_PREFIX = "sha256="


def valid_signature(body: bytes, header: str | None) -> bool:
    """
    Meta signs the raw body with the App Secret. The digest has to be taken over
    ``request.body`` exactly as received — re-serialising ``request.data`` changes
    whitespace and key order, and the check then fails on every real request.
    """
    secret = settings.WA_APP_SECRET
    if not secret or not header or not header.startswith(SIGNATURE_PREFIX):
        return False

    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), header.removeprefix(SIGNATURE_PREFIX).encode())


# Phone numbers are masked and message bodies never logged: whatever a guest
# or an employee writes to the hotel would otherwise live in log storage forever.


def handle_status(status: dict) -> None:
    recipient = mask_phone(status.get("recipient_id"))
    if status.get("status") == "failed":
        errors = [(e.get("code"), e.get("title")) for e in status.get("errors") or [] if isinstance(e, dict)]
        logger.warning("WhatsApp message %s to %s failed: %s", status.get("id"), recipient, errors)
        return

    logger.info("WhatsApp message %s to %s: %s", status.get("id"), recipient, status.get("status"))


def handle_message(message: dict) -> None:
    logger.info(
        "WhatsApp message %s from %s, type %s", message.get("id"), mask_phone(message.get("from")), message.get("type")
    )


def handle_payload(payload: dict) -> None:
    if payload.get("object") != "whatsapp_business_account":
        logger.info("Ignoring webhook for object %r", payload.get("object"))
        return

    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "messages":
                continue

            value = change.get("value") or {}
            for status in value.get("statuses") or []:
                handle_status(status)
            for message in value.get("messages") or []:
                handle_message(message)


class MessengersView(APIView):
    """
    WhatsApp Cloud API webhook: GET is Meta's one-off subscription handshake,
    POST carries delivery statuses and incoming messages.

    Plain ``HttpResponse`` on purpose: DRF's ``Response`` would JSON-encode the
    challenge into ``"12345"`` with quotes, and Meta rejects that.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request):
        token = settings.WA_VERIFY_TOKEN
        if (
            token
            and request.GET.get("hub.mode") == "subscribe"
            and hmac.compare_digest(request.GET.get("hub.verify_token", "").encode(), token.encode())
        ):
            return HttpResponse(request.GET.get("hub.challenge", ""), content_type="text/plain")
        return HttpResponse(status=403)

    def post(self, request):
        # ``request.body`` before anything touches ``request.data``: once DRF has
        # parsed the stream the raw bytes are no longer readable.
        body = request.body
        if not valid_signature(body, request.META.get(SIGNATURE_HEADER)):
            logger.warning("WhatsApp webhook rejected: bad or missing X-Hub-Signature-256")
            return HttpResponse(status=403)

        try:
            payload = json.loads(body)
        except ValueError:
            return HttpResponse(status=400)

        # Meta retries anything that is not a 200, for days, so a bug in the
        # handling must not turn into a retry storm of the same event.
        try:
            handle_payload(payload)
        except Exception:
            logger.exception("WhatsApp webhook handling failed")

        return HttpResponse(status=200)
