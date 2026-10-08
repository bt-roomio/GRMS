import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="admin_panel.tasks.send_activation_email")
def send_activation_email(user_id):
    from users.models import User
    from users.utils.emails import send_reset_link_email

    try:
        user = User.objects.get(id=user_id, is_active=True)
        send_reset_link_email(user, send_activation_mail=True)
        logger.info("Activation email sent to user %s", user_id)
    except User.DoesNotExist:
        logger.error("User %s not found or inactive", user_id)
        raise
