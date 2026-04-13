from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend


class TestEmailBackend(BaseEmailBackend):
    def send_messages(self, messages):
        mail.outbox.extend(messages)
        return len(messages)
