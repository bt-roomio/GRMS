from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def remove_default_permissions(sender, **kwargs):
    # List of core models for which to remove permissions
    models = [
        "tskv",
        "tenant",
        "session",
        "customer",
        "logentry",
        "relation",
        "tskvlatest",
        "taskresult",
        "groupresult",
        "attributekv",
        "contenttype",
        "chordcounter",
        "periodictask",
        "periodictasks",
        "tenantprofile",
        "tskvdictionary",
        "solarschedule",
        "clockedschedule",
        "crontabschedule",
        "intervalschedule",
        "devicecredentials",
    ]

    content_types = ContentType.objects.filter(model__in=models)
    Permission.objects.filter(content_type__in=content_types).delete()
    content_types.delete()
