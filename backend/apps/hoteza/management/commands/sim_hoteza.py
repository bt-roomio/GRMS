import json
import sys

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse

URL_NAMES = {
    "checkin": "hoteza-integration:checkin-list-view",
    "checkout": "hoteza-integration:checkout-list-view",
    "guestchange": "hoteza-integration:guest-change-view",
    "dnd": "hoteza-integration:dnd-view",
}


class Command(BaseCommand):
    help = "Simulate a Hoteza webhook: pass the event and its JSON payload (or '-' to read it from stdin)"

    def add_arguments(self, parser):
        parser.add_argument("event", choices=list(URL_NAMES))
        parser.add_argument("payload", nargs="?", default="-", help="JSON body, '-' reads stdin (default)")
        parser.add_argument("--url", help="Base URL of a running instance, default: in-process request")
        parser.add_argument("--ip", help="Client IP, default: first IP from HOTEZA_WHITELIST")

    def handle(self, event, payload, url, ip, **options):
        payload = json.loads(sys.stdin.read() if payload == "-" else payload)
        ip = ip or next(iter(settings.HOTEZA_WHITELIST), "127.0.0.1")
        path = reverse(URL_NAMES[event])

        self.stdout.write(f"POST {url or ''}{path} {json.dumps(payload, ensure_ascii=False)}")

        if url:
            response = requests.post(url.rstrip("/") + path, json=payload, headers={"X-Forwarded-For": ip}, timeout=30)
            status, body = response.status_code, response.text
        else:
            response = Client(REMOTE_ADDR=ip, HTTP_HOST=next(iter(settings.ALLOWED_HOSTS), "testserver")).post(
                path, data=payload, content_type="application/json"
            )
            status, body = response.status_code, response.content.decode(errors="replace")

        style = self.style.SUCCESS if 200 <= status < 300 else self.style.ERROR
        self.stdout.write(style(f"HTTP {status} {body}"))
