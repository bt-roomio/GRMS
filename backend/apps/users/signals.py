from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.utils.cache import invalidate_quick_cache
from users.models import Role, User


@receiver([post_save, post_delete], sender=User)
def staff_cache_invalidate(instance: User, **kwargs):
    if instance.tenant_id:
        invalidate_quick_cache("staffs", instance.tenant_id)


@receiver([post_save, post_delete], sender=Role)
def role_cache_invalidate(instance: Role, **kwargs):
    invalidate_quick_cache("roles", instance.tenant_id)
