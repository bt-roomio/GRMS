from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string

from rest_framework.exceptions import ValidationError

from main.models import EmailConfiguration
from users.models import ResetPassword


def send_reset_link_email(user, send_activation_mail=True):
    if not user.tenant:
        raise ValidationError({"detail": "User has no tenant."})

    config = EmailConfiguration.objects.filter(tenant=user.tenant).first()

    reset_key = ResetPassword.objects.create(user=user)

    host = config.frontend_host if config and config.frontend_host else "localhost"
    port = ":" + config.frontend_port if config and config.frontend_port else ""

    host = host.rstrip("/")
    url = f"{host}{port}" + "/password/new/" + "?key=" + reset_key.key

    if not send_activation_mail or not config:
        return bytes(url, encoding="utf-8")

    body = render_to_string("../templates/base_email.html", {"user": user, "url": url})
    subject = "Reset password, %s"

    backend = EmailBackend(
        host=config.host,
        port=int(config.port),
        username=config.email,
        password=config.password,
        use_tls=config.use_tls,
        fail_silently=True,
    )

    print(settings.TESTING)
    if settings.TESTING:
        return b"Activation link sent."

    res = send_mail(
        subject % config.username or settings.COMPANY_NAME,
        body,
        config.email,
        [user.email],
        html_message=body,
        connection=backend,
    )

    if not res:
        reset_key.delete()
        raise ValidationError({"detail": "Email configuration is not configured or is incorrect."})

    return b"Activation link sent."
