from django.template.loader import render_to_string
from django.conf import settings


def send_reset_link_email(request, reset, user):
    url = f'{settings.FRONTEND_DOMAIN}/reset-password/{reset.key}'
    text = render_to_string('reset_password.html', {'user': user, 'url': url}, request)
    subject = f'Reset password, {settings.COMPANY_NAME}'
    user.email_user(subject, text, from_email=settings.DEFAULT_FROM_EMAIL, html_message=text)
