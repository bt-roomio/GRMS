from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework.exceptions import ValidationError

from main.models import EmailConfiguration


def send_reset_link_email(request, user):
    url = f'{settings.FRONTEND_DOMAIN}/reset'
    body = render_to_string('reset_password.html', {'user': user, 'url': url}, request)
    subject = 'Reset password, %s'

    if user.tenant:
        config = EmailConfiguration.objects.filter(tenant=user.tenant).first()

        if not config:
            raise ValidationError({'detail': 'EmailConfiguration not found.'})

        backend = EmailBackend(host=config.host, port=int(config.port), username=config.email,
                               password=config.password, use_tls=config.use_tls, fail_silently=True)

        res = send_mail(subject % config.username or settings.COMPANY_NAME, body, config.email,
                        [user.email], html_message=body, connection=backend)
        return {'to': user.email, 'success': bool(res)}
    return {'to': user.email, 'success': False}
