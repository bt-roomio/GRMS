from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string

from rest_framework.exceptions import ValidationError

from users.models import ResetPassword


def send_reset_link_email(user, send_activation_mail=True):
    if not user.tenant:
        raise ValidationError({"detail": "User has no tenant."})

    reset_key = ResetPassword.objects.create(user=user)

    host = settings.FRONTEND_HOST or "localhost"
    port = ":" + str(settings.FRONTEND_PORT) or ""

    host = host.rstrip("/")
    url = f"{host}{port}" + "/password/new/" + "?key=" + reset_key.key

    if not send_activation_mail:
        return bytes(url, encoding="utf-8")

    body = render_to_string("../templates/base_email.html", {"user": user, "url": url})
    subject = "Reset password, %s" % settings.COMPANY_NAME

    backend = EmailBackend(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        fail_silently=False,
    )

    if settings.TESTING:
        return b"Activation link sent."

    res = send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
        [user.email],
        html_message=body,
        connection=backend,
    )


    if not res:
        reset_key.delete()
        raise ValidationError({"detail": "Email configuration is not configured or is incorrect."})

    return b"Activation link sent."
