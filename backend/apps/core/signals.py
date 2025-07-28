from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from users.models import Role


### =>>> It is disabled and enabled using custom permissions in models meta. Removing unnecessary permissions can lead to filtering.
# @receiver(post_migrate)
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
    give_perms()


def gen_perms():
    """
    comment lines enabled in models
    """
    content_types = [
        # {"app_label": "main", "model": "alarmsettings"},
        # {"app_label": "main", "model": "devicefromconf"},
        # {"app_label": "main", "model": "generalsettings"},
        # {"app_label": "main", "model": "integrationsettings"},
        # {"app_label": "main", "model": "roomfromconf"},
        # {"app_label": "main", "model": "roomstatus"},
        # {"app_label": "main", "model": "dashboardtype"},
        # {"app_label": "shuttle", "model": "attributelist"},
        # {"app_label": "shuttle", "model": "attributerpc"},
        # {"app_label": "shuttle", "model": "controllerfile"},
        # {"app_label": "shuttle", "model": "jsonrpc"},
        # {"app_label": "shuttle", "model": "guestmoveroom"},
        # {"app_label": "shuttle", "model": "removeattribute"},
    ]
    permissions = {"Can add ": "add_", "Can change ": "change_", "Can delete ": "delete_", "Can view ": "view_"}
    for i in content_types:
        app_label, model = i["app_label"], i["model"]
        content_type, _ = ContentType.objects.get_or_create(model=model, defaults={"app_label": app_label})
        for name, codename in permissions.items():
            Permission.objects.get_or_create(
                codename=codename + model, content_type=content_type, defaults={"name": name + model}
            )


def give_perms():
    tenant_admins = Role.objects.filter(name__in=["TENANT_ADMIN", "SYS_ADMIN"])
    permissions = Permission.objects.all()
    for tenant_admin in tenant_admins:
        tenant_admin.permissions.clear()
        tenant_admin.permissions.add(*permissions)
