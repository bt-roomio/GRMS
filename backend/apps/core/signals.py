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

    # TODO: optimise
    content_types = ContentType.objects.filter(model__in=models)
    Permission.objects.filter(content_type__in=content_types).delete()
    content_types.delete()
    gen_perms()


def gen_perms():
    content_types = [
        {"app_label": "main", "model": "alarmsettings"},
        {"app_label": "main", "model": "devicecredentials"},
        {"app_label": "main", "model": "devicefromconf"},
        {"app_label": "main", "model": "generalsettings"},
        {"app_label": "main", "model": "integrationsettings"},
        {"app_label": "main", "model": "roomfromconf"},
        {"app_label": "main", "model": "roomstatus"},
        {"app_label": "tenat", "model": "tenant"},
        {"app_label": "shuttle", "model": "attributelist"},
        {"app_label": "shuttle", "model": "attributerpc"},
        {"app_label": "shuttle", "model": "controllerfile"},
        {"app_label": "shuttle", "model": "jsonrpc"},
        {"app_label": "shuttle", "model": "tskvlatest"},
        {"app_label": "shuttle", "model": "relation"},
        {"app_label": "shuttle", "model": "tskv"},
        {"app_label": "shuttle", "model": "guestmoveroom"},
        {"app_label": "shuttle", "model": "removeattribute"},
        {"app_label": "users", "model": "permissions"},
    ]
    permissions = {"Can add ": "add_", "Can change ": "change_", "Can delete ": "delete_", "Can view ": "view_"}
    for i in content_types:
        app_label, model = i["app_label"], i["model"]
        content_type, _ = ContentType.objects.get_or_create(model=model, defaults={"app_label": app_label})
        for name, codename in permissions.items():
            Permission.objects.update_or_create(
                codename=codename + model, content_type=content_type, defaults={"name": name + model}
            )
