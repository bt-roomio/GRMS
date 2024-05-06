from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string
from django.conf import settings

from main.models import AdminSettings
from users.utils.validations import mail_fields


def send_reset_link_email(request, user):
    url = f'{settings.FRONTEND_DOMAIN}/reset'
    body = render_to_string('reset_password.html', {'user': user, 'url': url}, request)
    subject = f'Reset password, {settings.COMPANY_NAME}'

    if user.tenant:
        config = AdminSettings.objects.filter(tenant=user.tenant, key='mail').first()
        if config:
            host, port, from_email, password, use_tls = mail_fields(config.json_value)
            backend = EmailBackend(
                host=host, port=int(port), username=from_email, password=password, use_tls=use_tls, fail_silently=True)
            user.email_user(
                subject, body, from_email=settings.DEFAULT_FROM_EMAIL, html_message=body, connection=backend)
            return

    user.email_user(subject, body, from_email=settings.DEFAULT_FROM_EMAIL, html_message=body)
